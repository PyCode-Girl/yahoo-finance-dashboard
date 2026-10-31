export function Loading({ text = "Loading..." }) {
  return (
    <div className="state" role="status">
      <div className="spinner" />
      {text}
    </div>
  );
}

export function Empty({ text }) {
  return <div className="state">{text}</div>;
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}