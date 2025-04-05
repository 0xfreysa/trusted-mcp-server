import * as Comlink from 'comlink';
import init, {
  verify_code_attestation,
  verify_attestation_signature,
} from 'tee-verifier-js';

Comlink.expose({
  init,

  verify_code_attestation,
  verify_attestation_signature,
});
