import React, { ReactElement, useEffect, useState, useRef } from 'react';
import { CheckCircle, RefreshCw, XCircle } from 'lucide-react';
import * as Comlink from 'comlink';
const { init, verify_code_attestation }: any = Comlink.wrap(
  new Worker(new URL('../utils/worker.ts', import.meta.url)),
);

// Utility function to convert hex to base64
const hexToBase64 = (hexString: string): string => {
  // Remove any spaces or 0x prefix
  const cleanedHexString = hexString.replace(/^0x|\s+/g, '');
  // Convert hex to bytes
  const bytes = new Uint8Array(cleanedHexString.match(/.{1,2}/g)?.map(byte => parseInt(byte, 16)) || []);
  // Convert bytes to base64
  return btoa(String.fromCharCode.apply(null, Array.from(bytes)));
};

export function VerifyMCP(): ReactElement {
  const [processingVerification, setProcessingVerification] = useState(false);
  const [resultVerify, setResultVerify] = useState<boolean | null>(null);
  const [expectedPcrHex, setExpectedPcrHex] = useState('5591c9354a1d280817ee1230a108c4c343d53fe66e2d8acc84340ddd4fe918d1144606c0cd9ea7f3a090ac3497c1854f');
  const [codeAttestation, setCodeAttestation] = useState<null | string>(
    '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'
  );
  const [error, setError] = useState<null | string>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Function to auto-resize textarea
  const autoResizeTextarea = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  };

  // Call resize on content change
  useEffect(() => {
    autoResizeTextarea();
  }, [codeAttestation]);

  const verify_attestation_document = async () => {
    if (!codeAttestation) {
      setError('Please enter a valid code attestation');
      return;
    }
    const codeAttestation_ = codeAttestation.replace(/\\n/g, '').trim();
    const nonce = '0000000000000000000000000000000000000000';
    
    // Convert hex PCR to base64 for verification
    let expectedPcrBase64;
    try {
      expectedPcrBase64 = hexToBase64(expectedPcrHex);
    } catch (e) {
      setError('Invalid hex format for PCR');
      return;
    }

    setProcessingVerification(true);

    try {
      const resultVerify = await verify_code_attestation(
        codeAttestation_,
        nonce,
        expectedPcrBase64,
        Math.floor(Date.now() / 1000),
      );
      setResultVerify(resultVerify);
    } catch (e) {
      console.log('error', e);
      setResultVerify(false);
      setError((e as Error).message);
    } finally {
      setProcessingVerification(false);
    }
  };
  useEffect(() => {
    const initialize = async () => {
      await init({ loggingLevel: 'Debug' });
    };

    initialize();
  }, []);

  return (
    <div>
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden md:max-w-2xl">
        <div className="flex justify-between items-center mb-4"></div>

        <div className="mt-2 h-30 overflow-y-auto border border-gray-200 rounded p-4 mb-4">
          <h1 className="text-2xl font-bold text-center my-4">
            Verify MCP Server
          </h1>
          <div className="mb-4">
            <h2 className="text-l font-bold">Expected PCR2 Hash</h2>
            <pre className="bg-gray-100 p-2 rounded text-xs mt-2 mb-2 overflow-x-auto">
              <code>$ nitro-cli describe-enclaves | jq -r '.[0].Measurements.PCR2'</code>
            </pre>
            <textarea
              id="expectedPcr"
              name="expectedPcr"
              className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm font-mono"
              placeholder="Expected PCR value in hex format (e.g., 559249354a1d2808...)"
              value={expectedPcrHex}
              onChange={(e) => setExpectedPcrHex(e.target.value)}
            />
          </div>

          <h2 className="text-l font-bold">Code attestation</h2>
          <pre className="bg-gray-100 p-2 rounded text-xs mt-2 mb-2 overflow-x-auto">
            <code>$ curl -k https://127.0.0.1:443/enclave/attestation?nonce=0000000000000000000000000000000000000000</code>
          </pre>
          <textarea
            ref={textareaRef}
            id="attestation"
            name="attestation"
            className="mt-1 block w-full min-h-64 overflow-y-auto rounded-md border border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm font-mono"
            placeholder={
              codeAttestation ||
              'Paste the attestation object from the MCP'
            }
            onChange={(e) => {
              setCodeAttestation(e.target.value);
              // Call the resize function after setting the new value
              setTimeout(autoResizeTextarea, 0);
            }}
          />
        </div>

        <div className="p-8">
          <div className="flex justify-between items-center mb-4">
            <button
              onClick={verify_attestation_document}
              disabled={processingVerification}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center mx-auto"
            >
              {processingVerification ? (
                <>
                  <RefreshCw className="animate-spin -ml-1 mr-2 h-5 w-5" />
                  Verifying...
                </>
              ) : (
                <>
                  <CheckCircle className="mr-2 h-5 w-5" />
                  Verify Attestation
                </>
              )}
            </button>
          </div>

          {resultVerify !== null && (
            <div
              className={`mb-4 mt-4 p-4 rounded-md ${resultVerify ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
            >
              <div className="flex items-center ">
                {!resultVerify && <XCircle className="h-5 w-5 mr-2" />}

                {resultVerify ? (
                  <div>
                    ✅ Code hash matches open-source implementation <br />✅
                    Attestation verified against Amazon's root-of-trust <br />✅
                    Hardware instance authenticity confirmed
                  </div>
                ) : (
                  <span className="font-medium">
                    Remote attestation is invalid
                  </span>
                )}
                {!resultVerify && <p>{error}</p>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
