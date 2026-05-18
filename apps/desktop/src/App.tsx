import { Overlay } from "@/components/Overlay";
import { useGuideeStore } from "@/stores/guidee";
import { useEffect } from "react";
import { listen } from "@tauri-apps/api/event";

export default function App() {
  const addMessage = useGuideeStore((s) => s.addMessage);
  const setOverlayVisible = useGuideeStore((s) => s.setOverlayVisible);

  useEffect(() => {
    const unsubs: Array<() => void> = [];

    listen<string>("transcription-ready", (event) => {
      if (event.payload) {
        addMessage({ role: "user", content: event.payload });
      }
    }).then((u) => unsubs.push(u));

    listen("toggle-overlay", () => {
      setOverlayVisible(!useGuideeStore.getState().overlayVisible);
    }).then((u) => unsubs.push(u));

    listen("capture-and-ask", () => {
      setOverlayVisible(true);
    }).then((u) => unsubs.push(u));

    return () => unsubs.forEach((u) => u());
  }, [addMessage, setOverlayVisible]);

  return <Overlay />;
}
