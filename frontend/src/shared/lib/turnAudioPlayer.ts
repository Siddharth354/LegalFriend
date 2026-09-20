let sharedAudio: HTMLAudioElement | null = null;
let unlocked: boolean = false;
let currentTurnId: string | null = null;

function buildSilentWavUrl(): string {
  const buffer: ArrayBuffer = new ArrayBuffer(44 + 2);
  const view: DataView = new DataView(buffer);
  const writeString = (offset: number, value: string): void => {
    for (let index: number = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, 22050, true);
  view.setUint32(28, 22050 * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, 2, true);
  view.setInt16(44, 0, true);

  const blob: Blob = new Blob([buffer], { type: "audio/wav" });
  return URL.createObjectURL(blob);
}

function getSharedAudio(): HTMLAudioElement {
  if (!sharedAudio) {
    sharedAudio = new Audio();
    sharedAudio.preload = "auto";
  }
  return sharedAudio;
}

export function getSharedAudioElement(): HTMLAudioElement {
  return getSharedAudio();
}

export function getCurrentTurnId(): string | null {
  return currentTurnId;
}

export function unlockTurnAudio(): void {
  if (unlocked) return;
  unlocked = true;
  const audio: HTMLAudioElement = getSharedAudio();
  const url: string = buildSilentWavUrl();
  audio.muted = true;
  audio.src = url;
  audio
    .play()
    .then((): void => {
      audio.pause();
      audio.muted = false;
      URL.revokeObjectURL(url);
    })
    .catch((): void => {
      unlocked = false;
      audio.muted = false;
      URL.revokeObjectURL(url);
    });
}

export function playTurnAudio(turnId: string, url: string): Promise<void> {
  const audio: HTMLAudioElement = getSharedAudio();
  audio.muted = false;
  if (currentTurnId !== turnId || audio.src !== url) {
    audio.src = url;
    currentTurnId = turnId;
  }
  return audio.play();
}

export function pauseTurnAudio(): void {
  sharedAudio?.pause();
}
