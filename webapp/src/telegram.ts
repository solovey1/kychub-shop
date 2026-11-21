import { useEffect, useRef } from "react";

export const tg = window.Telegram?.WebApp;
export const initData = tg?.initData ?? "";

export function startTelegram() {
  tg?.ready();
  tg?.expand();
  tg?.setHeaderColor("secondary_bg_color");
}

export const close = () => tg?.close();
export const success = () => tg?.HapticFeedback.notificationOccurred("success");
export const failure = () => tg?.HapticFeedback.notificationOccurred("error");

export const confirm = (message: string) =>
  new Promise<boolean>((resolve) => (tg ? tg.showConfirm(message, resolve) : resolve(false)));

export const alert = (message: string) =>
  new Promise<void>((resolve) => (tg ? tg.showAlert(message, () => resolve()) : resolve()));

type Main = { busy?: boolean; destructive?: boolean };

/** The native MainButton: shown while the screen is mounted and `text` is set. A tap during
 * `busy` is ignored and the button shows its spinner. */
export function useMainButton(text: string | null, onClick: () => void, o: Main = {}) {
  const click = useRef(onClick);
  click.current = onClick;
  const busy = useRef(false);
  busy.current = !!o.busy;
  useEffect(() => {
    const b = tg?.MainButton;
    if (!tg || !b || text === null) return;
    const handler = () => busy.current || click.current();
    b.setText(text);
    b.setParams(
      o.destructive
        ? { color: tg.themeParams.destructive_text_color ?? "#d93636", text_color: "#ffffff" }
        : {
            color: tg.themeParams.button_color ?? "#2481cc",
            text_color: tg.themeParams.button_text_color ?? "#ffffff",
          },
    );
    b.show();
    b.onClick(handler);
    return () => {
      b.offClick(handler);
      b.hideProgress();
      b.hide();
    };
  }, [text, o.destructive]);
  useEffect(() => {
    if (text === null) return;
    if (o.busy) tg?.MainButton.showProgress(true);
    else tg?.MainButton.hideProgress();
  }, [o.busy, text]);
}

export function useBackButton(show: boolean, onClick: () => void) {
  const click = useRef(onClick);
  click.current = onClick;
  useEffect(() => {
    const b = tg?.BackButton;
    if (!b || !show) return;
    const handler = () => click.current();
    b.show();
    b.onClick(handler);
    return () => {
      b.offClick(handler);
      b.hide();
    };
  }, [show]);
}
