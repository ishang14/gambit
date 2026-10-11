export default function TextField({ label, id, className = '', ...inputProps }) {
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      <input id={id} name={id} className={`input ${className}`} {...inputProps} />
    </div>
  )
}
