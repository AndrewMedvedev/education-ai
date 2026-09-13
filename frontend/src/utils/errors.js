export function getErrorMessage(error, fallbackMessage) {
  return error?.userMessage || error?.message || fallbackMessage;
}
