import { useEffect, useRef, useState } from 'react'

const DURATION_MS = 160

interface AnimatedNumberProps {
  value: number
  format: (value: number) => string
}

/** Eases from the previous value to the new one. The first render shows the value directly. */
export function AnimatedNumber({ value, format }: AnimatedNumberProps) {
  const [shown, setShown] = useState(value)
  const shownRef = useRef(value)
  const frameRef = useRef(0)

  useEffect(() => {
    const from = shownRef.current
    if (from === value) return undefined
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const duration = reduced ? 0 : DURATION_MS
    const started = performance.now()

    function step(now: number) {
      const t = duration === 0 ? 1 : Math.min((now - started) / duration, 1)
      const eased = 1 - (1 - t) ** 3
      shownRef.current = from + (value - from) * eased
      setShown(shownRef.current)
      if (t < 1) frameRef.current = requestAnimationFrame(step)
    }

    frameRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frameRef.current)
  }, [value])

  return <>{format(shown)}</>
}
