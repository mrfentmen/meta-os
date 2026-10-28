// Still-image input helpers for the web frontend. A chosen image file is
// read in memory and sent once to the same assessment endpoint as a live
// camera frame; it is never stored by this app. Only the validation helper
// is pure; readFileAsDataURL needs the browser's FileReader.

export function isSupportedImageFile(file) {
  return (
    !!file &&
    typeof file.type === "string" &&
    file.type.toLowerCase().startsWith("image/")
  );
}

export function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    if (typeof FileReader === "undefined") {
      reject(new Error("This browser does not support reading files."));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () =>
      reject(new Error(reader.error ? reader.error.message : "Could not read the file."));
    reader.onabort = () => reject(new Error("Reading the file was cancelled."));
    reader.readAsDataURL(file);
  });
}
