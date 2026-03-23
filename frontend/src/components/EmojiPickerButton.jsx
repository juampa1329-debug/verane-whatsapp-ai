import React, { useEffect, useRef, useState } from "react";

const DEFAULT_EMOJIS = [
  "😀", "😁", "😂", "😊", "😍", "😘", "😎", "🤩",
  "🙏", "👏", "💪", "🔥", "⭐", "✅", "💬", "📦",
  "🛍️", "🎁", "💰", "📍", "⏰", "📞", "🧴", "🌸",
];

const btnStyle = {
  border: "1px solid rgba(255,255,255,0.18)",
  background: "transparent",
  color: "inherit",
  borderRadius: 9,
  width: 34,
  height: 34,
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: 16,
};

export default function EmojiPickerButton({
  onSelect,
  disabled = false,
  emojis = DEFAULT_EMOJIS,
  title = "Agregar emoji",
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    const onDocClick = (evt) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(evt.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  return (
    <div ref={rootRef} style={{ position: "relative", display: "inline-flex" }}>
      <button
        type="button"
        title={title}
        style={btnStyle}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
      >
        🙂
      </button>

      {open ? (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            right: 0,
            width: 220,
            maxHeight: 220,
            overflow: "auto",
            padding: 8,
            borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.16)",
            background: "#0b1217",
            boxShadow: "0 14px 26px rgba(0,0,0,0.4)",
            display: "grid",
            gridTemplateColumns: "repeat(8, 1fr)",
            gap: 6,
            zIndex: 1200,
          }}
        >
          {(emojis || []).map((emoji) => (
            <button
              type="button"
              key={emoji}
              style={{
                ...btnStyle,
                width: "100%",
                height: 30,
                borderRadius: 8,
                fontSize: 17,
              }}
              onClick={() => {
                onSelect?.(emoji);
                setOpen(false);
              }}
            >
              {emoji}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

