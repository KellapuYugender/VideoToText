import { useCallback, useEffect } from 'react'

const supported = typeof window !== 'undefined' && 'speechSynthesis' in window

/** Reads commentary aloud with the browser's built-in text-to-speech. */
export function useSpeech(enabled: boolean) {
  useEffect(() => {
    if (supported && !enabled) window.speechSynthesis.cancel()
  }, [enabled])

  useEffect(() => () => (supported ? window.speechSynthesis.cancel() : undefined), [])

  const speak = useCallback(
    (text: string) => {
      if (!supported || !enabled) return
      const synth = window.speechSynthesis
      // Live commentary: a stale line is worse than a cut-off one.
      synth.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      const voice = synth.getVoices().find((v) => v.lang.startsWith('en'))
      if (voice) utterance.voice = voice
      utterance.rate = 1.1
      synth.speak(utterance)
    },
    [enabled],
  )

  return { speak, supported }
}
