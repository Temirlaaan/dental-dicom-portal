import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';

interface TimeoutWarningProps {
  show: boolean;
  type: 'idle' | 'hard';
  onExtend: () => void;
  onEnd: () => void;
}

export default function TimeoutWarning({ show, type, onExtend, onEnd }: TimeoutWarningProps) {
  const isHard = type === 'hard';

  return (
    <Dialog open={show}>
      <DialogContent
        className={`border-t-4 ${isHard ? 'border-t-red-500' : 'border-t-amber-500'}`}
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className={isHard ? 'text-red-600' : 'text-amber-700'}>
            {isHard ? '⚠️ Session Ending Soon' : '💤 Idle Warning'}
          </DialogTitle>
          <DialogDescription className="text-slate-600 text-sm leading-relaxed">
            {isHard
              ? 'Your session will be automatically terminated in 10 minutes due to the session time limit.'
              : "You've been idle for 10 minutes. Click Extend to keep your session active."}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onEnd}>
            End Session
          </Button>
          <Button variant={isHard ? 'destructive' : 'warning'} onClick={onExtend}>
            Extend Session
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
