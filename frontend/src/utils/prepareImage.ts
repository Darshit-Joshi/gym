/**
 * Shrinks a photo in the browser before upload.
 *
 * Phone cameras produce 3-12 MB images; the server stores at most 1600 px anyway. Sending a
 * smaller JPEG saves mobile data and keeps uploads under hosting proxy limits (Vercel ~4.5 MB).
 * Small images, and anything the browser can't decode, are sent unchanged; the server still
 * validates every upload.
 */
const MAX_DIMENSION = 1600;
const SKIP_BELOW_BYTES = 1024 * 1024;
const JPEG_QUALITY = 0.85;

export async function prepareImageForUpload(file: File): Promise<File> {
  if (!file.type.startsWith('image/') || file.size < SKIP_BELOW_BYTES) return file;
  if (typeof createImageBitmap !== 'function') return file;

  try {
    // Applies the EXIF orientation so portrait phone photos stay upright
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height));
    const width = Math.round(bitmap.width * scale);
    const height = Math.round(bitmap.height * scale);

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      bitmap.close();
      return file;
    }
    ctx.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY),
    );
    if (!blob || blob.size >= file.size) return file;

    const name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
    return new File([blob], name, { type: 'image/jpeg', lastModified: file.lastModified });
  } catch {
    return file;
  }
}
