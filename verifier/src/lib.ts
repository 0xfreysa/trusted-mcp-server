import initWasm, {
  initThreadPool,
  init_logging,
  LoggingLevel,
  verify_attestation_document,
  verify_attestation_signature,
} from '../wasm/pkg/tlsn_wasm';

//import { verify_js } from '../wasm/remote-attestation-verifier/remote_attestation_verifier';

let LOGGING_LEVEL: LoggingLevel = 'Info';

function debug(...args: any[]) {
  if (['Debug', 'Trace'].includes(LOGGING_LEVEL)) {
    console.log('tlsn-js DEBUG', ...args);
  }
}

/**
 * Convert the PEM string represetation of a P256 public key to a hex string of its raw bytes
 * @param pemString - The PEM string to convert
 * @returns The raw hex string
 */
export function pemToRawHex(pemString: string) {
  const base64 = pemString
    .replace('-----BEGIN PUBLIC KEY-----', '')
    .replace('-----END PUBLIC KEY-----', '')
    .replace(/\s/g, '');
  return Buffer.from(base64, 'base64').toString('hex').slice(-130);
}

/**
 * It generates a random nonce of length 40 using hexadecimal characters.
 * This nonce is used to ensure the uniqueness of the attestation.
 * @returns {string} The generated nonce.
 */

export function generateNonce() {
  return Array.from({ length: 40 }, () =>
    Math.floor(Math.random() * 16).toString(16),
  ).join('');
}

export { verify_attestation_signature };

export async function verify_code_attestation(
  remote_attestation_base64: string,
  expected_nonce: string,
  expected_pcr: string,
  timestamp: number = Math.floor(Date.now() / 1000),
) {
  return await verify_attestation_document(
    remote_attestation_base64,
    expected_nonce,
    expected_pcr,
    BigInt(timestamp),
  );
}

export default async function init(config?: {
  loggingLevel?: LoggingLevel;
  hardwareConcurrency?: number;
}) {
  const {
    loggingLevel = 'Info',
    hardwareConcurrency = navigator.hardwareConcurrency,
  } = config || {};

  LOGGING_LEVEL = loggingLevel;

  const res = await initWasm();

  init_logging({
    level: loggingLevel,
    crate_filters: undefined,
    span_events: undefined,
  });

  // 6422528 ~= 6.12 mb
  debug('res.memory=', res.memory);
  debug('res.memory.buffer.length=', res.memory.buffer.byteLength);
  debug('DEBUG', 'initialize thread pool');

  await initThreadPool(hardwareConcurrency);
  debug('initialized thread pool');

  return true;
}
