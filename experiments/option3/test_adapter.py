"""Adapter contract tests with fake engine; no pretrained model run claimed."""
import base64
import tempfile
from pathlib import Path
import talking_head as th


def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)
        engine=root/'SadTalker';(engine/'checkpoints').mkdir(parents=True)
        (engine/'inference.py').write_text('')
        for n in th.REQUIRED_MODELS:
            (engine/'checkpoints'/n).write_bytes(b'x'*1001)
        py=root/'python.exe';py.write_text('fake')
        info=th.check_setup(str(py),engine=engine,ffmpeg='/mock/ffmpeg')
        assert info.ready,info.issues
        seen=[]
        original=th.save_image
        def fake_image(url,p):p.write_bytes(b'fake-jpeg')
        def fake_run(cmd,**kwargs):
            seen.append(cmd)
            if 'inference.py' in cmd:
                i=cmd.index('--result_dir');result=Path(cmd[i+1]);result.mkdir(parents=True,exist_ok=True)
                (result/'generated.mp4').write_bytes(b'mock-video'*150)
            else:
                Path(cmd[-1]).write_bytes(b'mock-wav'*100)
            class R:returncode=0;stdout='ok';stderr=''
            return R()
        th.save_image=fake_image
        try:
            args=dict(name='Alex',photo_url='https://images.unsplash.com/photo-test', audio_base64=base64.b64encode(b'fake-audio'*50).decode(),python_override=str(py),ffmpeg='/mock/ffmpeg',engine=engine,lab=root/'lab',run=fake_run)
            path=th.run_experiment(**args)
            assert path.exists() and path.stat().st_size>1000
            assert '--cpu' in seen[1] and '--batch_size' in seen[1]
            assert len(seen)==2
            path2=th.run_experiment(**args)
            assert path2==path and len(seen)==2
            print('PASS setup validator, isolated paths, WAV conversion command, CPU inference invocation, output, cache')
        finally:
            th.save_image=original

if __name__=='__main__':main()
