import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

export const BubbleEditor = ({ bubble, onClose, onSave }) => {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (bubble) setText(bubble.id); }, [bubble]);

  const save = async () => {
    setBusy(true);
    await onSave(text);
    setBusy(false);
  };

  return (
    <Dialog open={!!bubble} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="bg-[#0d0b14] text-[#f3eefc] border-white/10 rounded-3xl w-[92vw] max-w-md" data-testid="bubble-editor">
        <DialogHeader className="text-left">
          <DialogTitle className="disp text-3xl text-[#f3eefc]">Edit terjemahan</DialogTitle>
          <DialogDescription className="text-[#9e94b0]">Teks asli: {bubble?.en}</DialogDescription>
        </DialogHeader>
        <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} data-testid="bubble-editor-input"
          className="bg-white/5 border-white/15 text-[#f3eefc] text-base rounded-xl focus-visible:ring-[#ff3d6e]" />
        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onClose} data-testid="bubble-editor-cancel"
            className="rounded-full border border-white/20 px-5 h-11 text-sm">Batal</button>
          <button type="button" onClick={save} disabled={busy || !text.trim()} data-testid="bubble-editor-save"
            className="flex items-center gap-2 rounded-full bg-[#ff3d6e] text-[#0d0b14] px-5 h-11 text-sm font-semibold disabled:opacity-40">
            {busy && <Loader2 className="h-4 w-4 animate-spin" />} Simpan
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
