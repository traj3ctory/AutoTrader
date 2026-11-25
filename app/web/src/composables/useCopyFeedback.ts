import { ref } from "vue";
import { COPY_RESET_MS } from "../constants/analyzer";
import { CopyTarget } from "../types/analyzer";

export function useCopyFeedback() {
  const copiedTarget = ref<CopyTarget>(CopyTarget.None);

  function flashCopied(target: CopyTarget) {
    copiedTarget.value = target;
    window.setTimeout(() => {
      if (copiedTarget.value === target) {
        copiedTarget.value = CopyTarget.None;
      }
    }, COPY_RESET_MS);
  }

  async function copyToClipboard({ text, target }: { text: string; target: CopyTarget }) {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    flashCopied(target);
  }

  return { copiedTarget, flashCopied, copyToClipboard };
}
