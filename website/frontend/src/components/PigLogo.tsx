interface PigLogoProps {
  size?: number
  className?: string
}

const LOGO_VERSION = 2 // bump this when you replace the logo image

export default function PigLogo({ size = 32, className = '' }: PigLogoProps) {
  return (
    <img
      src={`/logo.png?v=${LOGO_VERSION}`}
      alt="Truffle AI"
      width={size}
      height={size}
      className={className}
      style={{ borderRadius: size * 0.2 }}
    />
  )
}
