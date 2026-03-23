import React, { Suspense, useEffect, useRef, useState } from "react";

const LazyEmojiPicker = React.lazy(() => import("emoji-picker-react"));

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

  useEffect(() => {
    if (disabled && open) setOpen(false);
  }, [disabled, open]);

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
            borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.16)",
            background: "#0b1217",
            boxShadow: "0 14px 26px rgba(0,0,0,0.4)",
            zIndex: 1200,
            overflow: "hidden",
          }}
        >
          <Suspense fallback={<div style={{ padding: 10, fontSize: 12, opacity: 0.8 }}>Cargando emojis...</div>}>
            <LazyEmojiPicker
              lazyLoadEmojis
              width={320}
              height={390}
              autoFocusSearch={false}
              searchDisabled={false}
              skinTonesDisabled={false}
              previewConfig={{ showPreview: false }}
              theme="dark"
              onEmojiClick={(emojiData) => {
                  onSelect?.(emojiData?.emoji || "");
                  setOpen(false);
              }}
            />
          </Suspense>
        </div>
      ) : null}
    </div>
  );
}
