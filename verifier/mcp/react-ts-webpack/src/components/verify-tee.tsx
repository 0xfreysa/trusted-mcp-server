import React, { ReactElement, useEffect, useState } from 'react';
import { CheckCircle, RefreshCw, XCircle } from 'lucide-react';
// import { Link } from 'react-router-dom';
import * as Comlink from 'comlink';

const { init, verify_code_attestation }: any = Comlink.wrap(
  new Worker(new URL('../utils/worker.ts', import.meta.url)),
);

const nonce = '0000000000000000000000000000000000000000';

const EXPECTED_PCRS = {
  '1': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
  '2': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
};

export function VerifyTee(): ReactElement {
  const [processingVerification, setProcessingVerification] = useState(false);

  const [resultVerify, setResultVerify] = useState<boolean | null>(null);

  const [codeAttestation, setCodeAttestation] = useState<null | string>('');
  const [error, setError] = useState<null | string>(null);

  const verify_attestation_document = async () => {
    if (!codeAttestation) {
      setError('Please enter a valid code attestation');
      return;
    }
    const codeAttestation_ = codeAttestation.replace(/\\n/g, '').trim();

    console.log('codeAttestation_', codeAttestation_);
    setProcessingVerification(true);
    try {
      const resultVerify = await verify_code_attestation(
        codeAttestation_,
        nonce,
        EXPECTED_PCRS,
        Math.floor(Date.now() / 1000),
      );

      setResultVerify(resultVerify);
    } catch (e) {
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
          <h2 className="text-l font-bold">
            {' '}
            1) Get your code attestation from enclave
          </h2>

          <h2 className="text-l font-bold">
            {' '}
            2) Paste code attestation in base64 format
          </h2>

          <textarea
            id="nonce"
            name="nonce"
            className="mt-1 block w-96 h-32 overflow-y-auto rounded-md border border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm"
            placeholder={codeAttestation ?? ''}
            onChange={(e) => setCodeAttestation(e.target.value)}
          />
        </div>

        <div className="p-8">
          <div className="flex justify-between items-center mb-4">
            <button
              onClick={verify_attestation_document}
              disabled={processingVerification}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {processingVerification ? (
                <>
                  <RefreshCw className="animate-spin -ml-1 mr-2 h-5 w-5" />
                  Verifying...
                </>
              ) : (
                <>
                  <CheckCircle className="mr-2 h-5 w-5" />
                  Verify Remote Attestation
                </>
              )}
            </button>
          </div>

          {resultVerify !== null && (
            <div
              className={`mt-4 p-4 rounded-md ${resultVerify ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
            >
              <div className="flex items-center">
                {resultVerify ? (
                  <CheckCircle className="h-5 w-5 mr-2" />
                ) : (
                  <XCircle className="h-5 w-5 mr-2" />
                )}
                <span className="font-medium">
                  {resultVerify
                    ? 'Remote attestation is valid'
                    : 'Remote attestation is invalid'}
                  {!resultVerify && <p>{error}</p>}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
