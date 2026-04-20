const VIDEO_EXTENSIONS = new Set([".mp4", ".mov", ".avi", ".m4v", ".mpeg", ".mpg", ".webm"]);

export function isVideoAssetFilename(filename: string): boolean {
  const normalized = filename.trim().toLowerCase();
  for (const extension of VIDEO_EXTENSIONS) {
    if (normalized.endsWith(extension)) {
      return true;
    }
  }
  return false;
}