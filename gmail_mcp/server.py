# Imports
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from fastapi import FastAPI
import uvicorn
import asyncio
from datetime import datetime, timedelta
import email
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import unquote
from dataclasses import dataclass
import ssl
from loguru import logger
import sys
import uuid
from starlette.requests import Request
from weakref import WeakValueDictionary

# Setup logging
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# Constants
SEARCH_TIMEOUT = 60  # seconds
MAX_EMAILS = 100

# Setup FastAPI app and MCP server
app = FastAPI()
mcp = FastMCP("Email Client")

# Global session management - using WeakValueDictionary to allow garbage collection
# and avoid memory leaks when connections close
ACTIVE_SESSIONS = WeakValueDictionary()

#################################
# DATACLASSES
#################################


@dataclass
class DateRange:
    """Date range operations for email searches"""

    start: str | None = None
    end: str | None = None

    @staticmethod
    def format_date(
        date_str: str | None, default_days_ago: int = 0
    ) -> tuple[datetime, str]:
        """Format a date string to IMAP format, with default if None"""
        if date_str:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            date_obj = datetime.now() - timedelta(days=default_days_ago)
        return date_obj, date_obj.strftime("%d-%b-%Y")

    def get_days(self) -> list[datetime]:
        """Get all days in the date range (inclusive)"""
        start_obj, _ = self.format_date(self.start, 7)  # Default 7 days ago
        end_obj, _ = self.format_date(self.end, 0)  # Default today

        days = []
        current = start_obj
        while current <= end_obj:
            days.append(current)
            current += timedelta(days=1)
        return days


class SearchCriteria:
    """Builder for IMAP search criteria strings"""

    @staticmethod
    def create_date_criteria(start: str | None = None, end: str | None = None) -> str:
        """Create IMAP search criteria for date range"""
        start_obj, start_fmt = DateRange.format_date(start, 7)  # Default 7 days ago
        end_obj, end_fmt = DateRange.format_date(end, 0)  # Default today

        # Build date criteria
        if start_fmt == end_fmt:
            # If searching for a single day
            return f'ON "{start_fmt}"'
        else:
            # Calculate next day for BEFORE (which is exclusive)
            next_day = (end_obj + timedelta(days=1)).strftime("%d-%b-%Y")
            return f'SINCE "{start_fmt}" BEFORE "{next_day}"'

    @staticmethod
    def create_search_criteria(
        start: str | None = None, end: str | None = None, keyword: str | None = None
    ) -> str:
        """Create complete IMAP search string for the given parameters"""
        date_criteria = SearchCriteria.create_date_criteria(start, end)

        # Add keyword if provided
        if keyword:
            keyword_criteria = f'(OR SUBJECT "{keyword}" BODY "{keyword}")'
            return f"({keyword_criteria} {date_criteria})"

        return date_criteria


@dataclass
class EmailSummary:
    """Summary information about an email"""

    id: str
    sender: str = "Unknown"
    date: str = "Unknown"
    subject: str = "No Subject"

    def __str__(self) -> str:
        """Format email summary as a table row"""
        return f"{self.id} | {self.sender} | {self.date} | {self.subject}"

    @classmethod
    def from_message_data(cls, msg_data: tuple) -> "EmailSummary":
        """Create an EmailSummary from IMAP message data."""
        email_body = email.message_from_bytes(msg_data[0][1])

        return cls(
            id=msg_data[0][0].split()[0].decode(),  # Get the email ID
            sender=email_body.get("From", "Unknown"),
            date=email_body.get("Date", "Unknown"),
            subject=email_body.get("Subject", "No Subject"),
        )


@dataclass
class EmailContent(EmailSummary):
    """Full content of an email including body"""

    to: str = "Unknown"
    content: str = ""

    def __str__(self) -> str:
        """Format email content for display"""
        return (
            f"From: {self.sender}\n"
            f"To: {self.to}\n"
            f"Date: {self.date}\n"
            f"Subject: {self.subject}\n"
            f"\nContent:\n{self.content}"
        )

    @classmethod
    def from_message_data(cls, msg_data: tuple) -> "EmailContent":
        """Create an EmailContent from IMAP message data."""
        email_body = email.message_from_bytes(msg_data[0][1])

        # Extract body content
        body = ""
        if email_body.is_multipart():
            # Handle multipart messages
            for part in email_body.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
                elif part.get_content_type() == "text/html":
                    # If no plain text found, use HTML content
                    if not body:
                        body = part.get_payload(decode=True).decode()
        else:
            # Handle non-multipart messages
            body = email_body.get_payload(decode=True).decode()

        return cls(
            id=msg_data[0][0].split()[0].decode(),
            sender=email_body.get("From", "Unknown"),
            to=email_body.get("To", "Unknown"),
            date=email_body.get("Date", "Unknown"),
            subject=email_body.get("Subject", "No Subject"),
            content=body,
        )


@dataclass
class EmailResults:
    """Container for formatted email search results"""

    emails: list[EmailSummary]

    def format_table(self) -> str:
        """Format search results as a table"""
        if not self.emails:
            return "No emails found matching the criteria."

        result = "Found emails:\n\n"
        result += "ID | From | Date | Subject\n"
        result += "-" * 80 + "\n"

        for email_ in self.emails:
            result += f"{email_}\n"

        result += "\nUse get-email-content with an email ID to view the full content of a specific email."
        return result

    @classmethod
    def format_daily_counts(cls, date_counts: list[tuple[datetime, int | str]]) -> str:
        """Format daily email counts as a table"""
        result = "Daily email counts:\n\n"
        result += "Date | Count\n"
        result += "-" * 30 + "\n"

        for date, count in date_counts:
            result += f"{date.strftime('%Y-%m-%d')} | {count}\n"

        return result


class EmailMessageFactory:
    """Utility for creating email messages"""

    @staticmethod
    def create_message(
        from_email: str, to: list[str], subject: str, content: str, cc: list[str] = None
    ) -> MIMEMultipart:
        """Create an email message"""
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "plain", "utf-8"))
        return msg


@dataclass
class EmailSession:
    """Email connection credentials and server configuration"""

    email: str
    password: str
    imap_server: str = "imap.gmail.com"
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587

    @classmethod
    def from_request(cls, request: Request) -> "EmailSession | None":
        """Extract email session configuration from request parameters"""
        try:
            if "ADDR" in request.query_params and "ASP" in request.query_params:
                email_addr = unquote(request.query_params["ADDR"])
                password = unquote(request.query_params["ASP"])
                return cls(email=email_addr, password=password)
            else:
                logger.error("Missing required connection parameters")
        except Exception as e:
            logger.error(f"Config extraction error: {e}")

        return None

    @classmethod
    def from_current_session(cls) -> "EmailSession | None":
        """Get the current session configuration based on the current request"""
        # First try to get from mcp._current_request
        if hasattr(mcp, "_current_request"):
            request = mcp._current_request
            return cls.from_request(request)
        # Then try server request
        elif hasattr(mcp, "_mcp_server") and hasattr(mcp._mcp_server, "_request"):
            request = mcp._mcp_server._request
            return cls.from_request(request)
        else:
            logger.error("Cannot find request object")
            return None

    async def connect_imap(self, folder: str = "inbox"):
        """Connect to IMAP server and select folder"""
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.email, self.password)

        if folder == "sent":
            mail.select('"[Gmail]/Sent Mail"')  # For Gmail
        else:
            mail.select("inbox")

        return mail

    def close_imap(self, mail):
        """Safely close IMAP connection"""
        try:
            mail.close()
            mail.logout()
        except Exception as e:
            logger.error(f"IMAP close error: {e}")


#################################
# EMAIL ASYNC OPERATIONS
#################################


async def search_emails_async(
    mail: imaplib.IMAP4_SSL, search_criteria: str
) -> list[EmailSummary]:
    """Asynchronously search emails with timeout."""
    loop = asyncio.get_event_loop()
    try:
        _, messages = await loop.run_in_executor(
            None, lambda: mail.search(None, search_criteria)
        )
        if not messages[0]:
            return []

        email_list = []
        for num in messages[0].split()[:MAX_EMAILS]:  # Limit to MAX_EMAILS
            _, msg_data = await loop.run_in_executor(
                None, lambda: mail.fetch(num, "(RFC822)")
            )
            email_list.append(EmailSummary.from_message_data(msg_data))

        return email_list
    except Exception as e:
        raise Exception(f"Error searching emails: {str(e)}")


async def get_email_content_async(
    mail: imaplib.IMAP4_SSL, email_id: str
) -> EmailContent:
    """Asynchronously get full content of a specific email."""
    loop = asyncio.get_event_loop()
    try:
        _, msg_data = await loop.run_in_executor(
            None, lambda: mail.fetch(email_id, "(RFC822)")
        )
        return EmailContent.from_message_data(msg_data)
    except Exception as e:
        raise Exception(f"Error fetching email content: {str(e)}")


async def count_emails_async(mail: imaplib.IMAP4_SSL, search_criteria: str) -> int:
    """Asynchronously count emails matching the search criteria."""
    loop = asyncio.get_event_loop()
    try:
        _, messages = await loop.run_in_executor(
            None, lambda: mail.search(None, search_criteria)
        )
        return len(messages[0].split()) if messages[0] else 0
    except Exception as e:
        raise Exception(f"Error counting emails: {str(e)}")


async def send_email_async(
    to_addresses: list[str],
    subject: str,
    content: str,
    cc_addresses: list[str] | None = None,
    config: EmailSession = None,
) -> None:
    """Asynchronously send an email."""
    try:
        # Create message
        msg = EmailMessageFactory.create_message(
            from_email=config.email,
            to=to_addresses,
            subject=subject,
            content=content,
            cc=cc_addresses,
        )

        context = ssl.create_default_context()
        server = smtplib.SMTP(config.smtp_server, config.smtp_port)
        await asyncio.to_thread(server.starttls, context=context)
        await asyncio.to_thread(server.login, config.email, config.password)

        all_recipients = to_addresses
        if cc_addresses:
            all_recipients += cc_addresses

        await asyncio.to_thread(
            server.sendmail, config.email, all_recipients, msg.as_string()
        )
        server.quit()
    except Exception as e:
        logger.error(f"Error in send_email_async: {str(e)}")
        raise


#################################
# MCP TOOL FUNCTIONS
#################################


@mcp.tool()
async def search_emails(
    start_date: str = None,
    end_date: str = None,
    keyword: str = None,
    folder: str = "inbox",
) -> str:
    """Search emails within a date range and/or with specific keywords"""
    try:
        # Get session-specific config
        email_session = EmailSession.from_current_session()
        if not email_session:
            return "Error: No valid email configuration found for this session."

        # Connect to IMAP server using connection-specific credentials
        mail = imaplib.IMAP4_SSL(email_session.imap_server)
        mail.login(email_session.email, email_session.password)

        # Select folder
        if folder == "sent":
            mail.select('"[Gmail]/Sent Mail"')  # For Gmail
        else:
            mail.select("inbox")

        # Get search criteria
        search_criteria = SearchCriteria.create_search_criteria(
            start_date, end_date, keyword
        )

        try:
            async with asyncio.timeout(SEARCH_TIMEOUT):
                email_list = await search_emails_async(mail, search_criteria)

                # Format results using the EmailResults class
                results = EmailResults(email_list)
                return results.format_table()

        except asyncio.TimeoutError:
            return "Search operation timed out. Please try with a more specific search criteria."
        finally:
            email_session.close_imap(mail)
    except Exception as e:
        logger.error(f"Error in search_emails: {str(e)}")
        return f"An error occurred: {str(e)}"


@mcp.tool()
async def get_email_content(email_id: str) -> str:
    """Get the full content of a specific email by its ID"""
    try:
        # Get session-specific config
        email_session = EmailSession.from_current_session()
        if not email_session:
            return "Error: No valid email configuration found for this session."

        mail = await email_session.connect_imap()

        try:
            async with asyncio.timeout(SEARCH_TIMEOUT):
                email_content = await get_email_content_async(mail, email_id)
                return str(email_content)
        except asyncio.TimeoutError:
            return "Operation timed out while fetching email content."
        finally:
            email_session.close_imap(mail)
    except Exception as e:
        logger.error(f"Error in get_email_content: {str(e)}")
        return f"An error occurred: {str(e)}"


@mcp.tool()
async def count_daily_emails(start_date: str, end_date: str) -> str:
    """Count emails received for each day in a date range"""
    try:
        # Get session-specific config
        email_session = EmailSession.from_current_session()
        if not email_session:
            return "Error: No valid email configuration found for this session."

        mail = imaplib.IMAP4_SSL(email_session.imap_server)
        mail.login(email_session.email, email_session.password)
        mail.select("inbox")

        try:
            # Get all days in the range
            date_range = DateRange(start=start_date, end=end_date)
            days = date_range.get_days()

            date_counts = []
            for day in days:
                date_str = day.strftime("%d-%b-%Y")
                search_criteria = f'(ON "{date_str}")'

                try:
                    async with asyncio.timeout(SEARCH_TIMEOUT):
                        count = await count_emails_async(mail, search_criteria)
                        date_counts.append((day, count))
                except asyncio.TimeoutError:
                    date_counts.append((day, "Timeout"))

            # Format results using EmailResults class
            return EmailResults.format_daily_counts(date_counts)

        finally:
            email_session.close_imap(mail)
    except Exception as e:
        logger.error(f"Error in count_daily_emails: {str(e)}")
        return f"An error occurred: {str(e)}"


@mcp.tool()
async def send_email(
    to: list[str], subject: str, content: str, cc: list[str] = None
) -> str:
    """CONFIRMATION STEP: Actually send the email after user confirms the details."""
    if not to:
        return "At least one recipient email address is required."

    try:
        # No logging of email addresses or content

        # Get session-specific config
        email_session = EmailSession.from_current_session()
        if not email_session:
            return "Error: No valid email configuration found for this session."

        async with asyncio.timeout(SEARCH_TIMEOUT):
            await send_email_async(to, subject, content, cc, config=email_session)
            return "Email sent successfully!"
    except asyncio.TimeoutError:
        return "Operation timed out while sending email."
    except Exception as e:
        error_msg = str(e)
        return f"Failed to send email: {error_msg}\n\nPlease check:\n1. Email and password are correct\n2. SMTP settings are correct\n3. Less secure app access is enabled (for Gmail)\n4. Using App Password if 2FA is enabled"


#################################
# SERVER SETUP
#################################


def create_sse_server(mcp):
    """Create a Starlette app that handles SSE connections and message handling"""
    transport = SseServerTransport("/messages/")

    # Define handler functions
    async def handle_sse(request):
        # Generate a unique session ID for this connection
        session_id = str(uuid.uuid4())

        # No logging of connection details

        # Store request in session dictionary with unique ID
        ACTIVE_SESSIONS[session_id] = request

        async with transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            try:
                # Store the request object for later access by tools
                mcp._current_request = request

                await mcp._mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp._mcp_server.create_initialization_options(),
                )
            finally:
                # Clear the request reference
                if hasattr(mcp, "_current_request"):
                    delattr(mcp, "_current_request")
                # Remove from active sessions
                if session_id in ACTIVE_SESSIONS:
                    del ACTIVE_SESSIONS[session_id]
                    # No logging of session destruction

    # Create Starlette routes for SSE and message handling
    routes = [
        Route("/sse/", endpoint=handle_sse),
        Mount("/messages/", app=transport.handle_post_message),
    ]

    # Create a Starlette app
    return Starlette(routes=routes)


@app.get("/")
def read_root():
    """Health check endpoint"""
    return {"status": "Email Client Server is running"}


# Mount the Starlette SSE server onto the FastAPI app
app.mount("/", create_sse_server(mcp))


# Start the server
if __name__ == "__main__":
    # Minimal logging that doesn't reveal user information
    uvicorn.run(app, host="0.0.0.0", port=7047)
