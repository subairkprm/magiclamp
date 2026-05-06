/** Token-aware shimmer block used while remote content is loading. */
export default function Skeleton({ className = '', as: Tag = 'div' }) {
  return (
    <Tag
      aria-hidden="true"
      className={`animate-pulse rounded-md bg-elevated ${className}`}
    />
  )
}
