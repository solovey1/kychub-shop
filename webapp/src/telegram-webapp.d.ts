// Only what the app uses of https://core.telegram.org/bots/webapps
interface TgButton {
  show(): void;
  hide(): void;
  onClick(cb: () => void): void;
  offClick(cb: () => void): void;
}
interface TgMainButton extends TgButton {
  setText(text: string): void;
  setParams(p: { color?: string; text_color?: string; is_active?: boolean }): void;
  showProgress(leaveActive?: boolean): void;
  hideProgress(): void;
}
interface TgWebApp {
  initData: string;
  initDataUnsafe: { user?: { id: number; language_code?: string } };
  themeParams: Record<string, string>;
  colorScheme: "light" | "dark";
  MainButton: TgMainButton;
  BackButton: TgButton;
  HapticFeedback: { notificationOccurred(type: "success" | "error" | "warning"): void };
  ready(): void;
  expand(): void;
  close(): void;
  setHeaderColor(color: string): void;
  showConfirm(message: string, cb: (ok: boolean) => void): void;
  showAlert(message: string, cb?: () => void): void;
}
interface Window {
  Telegram?: { WebApp: TgWebApp };
}
