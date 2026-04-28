import { readFileSync } from "node:fs";
import { join } from "node:path";

const fixtureDir = join(__dirname, "..", "fixtures");

export const imageFixture = {
  name: "test-image.jpeg",
  mimeType: "image/jpeg",
  buffer: readFileSync(join(fixtureDir, "test-image.jpeg")),
};

export const videoFixture = {
  name: "test-video.mp4",
  mimeType: "video/mp4",
  buffer: readFileSync(join(fixtureDir, "test-video.mp4")),
};
