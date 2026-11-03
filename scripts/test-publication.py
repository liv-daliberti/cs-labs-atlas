import io,json,tarfile,tempfile,unittest,hashlib,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
import bootstrap,publish
class PublicationTests(unittest.TestCase):
    def test_failed_activation_restores_previous_release(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);old=root/'old';new=root/'new';old.mkdir();new.mkdir();(root/'current').symlink_to(old);calls=[]
            def restart():calls.append((root/'current').resolve())
            def fail():raise ValueError('smoke failed')
            with self.assertRaisesRegex(ValueError,'smoke failed'):publish.switch(root,new,restart,fail)
            self.assertEqual((root/'current').resolve(),old);self.assertEqual(calls,[new,old])
            publish.switch(root,new,restart,lambda:None)
            self.assertEqual(json.loads((root/'previous.json').read_text())['path'],str(old))
    def test_bootstrap_verifies_downloads_and_resumes_without_replacing_objects(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);payload=b'synthetic asset';sha=hashlib.sha256(payload).hexdigest();config={'schema':1,'release':'fixture','manifestSha256':sha}
            archive=root/'part'
            with tarfile.open(archive,'w:gz') as tar:
                for name,raw in [('config.json',json.dumps(config).encode()),('objects/'+sha,payload)]:
                    entry=tarfile.TarInfo(name);entry.size=len(raw);tar.addfile(entry,io.BytesIO(raw))
            class Quiet(SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                origin=f'http://127.0.0.1:{server.server_port}'
                catalog=root/'catalog.json';catalog.write_text(json.dumps({'config':config,'parts':[{'url':origin+'/part','sha256':bootstrap.digest(archive),'bytes':archive.stat().st_size}],'papers':[]}))
                pin={'url':origin+'/catalog.json','sha256':bootstrap.digest(catalog)};output=root/'publication'
                bootstrap.bootstrap(pin,output);inode=(output/'objects'/sha).stat().st_ino
                archive.write_bytes(b'bad remote replacement')
                bootstrap.bootstrap(pin,output)
                self.assertEqual((output/'objects'/sha).stat().st_ino,inode)
                with self.assertRaisesRegex(ValueError,'checksum'):
                    bootstrap.download(origin+'/part',root/'fresh','0'*64)
            finally:server.shutdown();server.server_close();thread.join()
    def test_bootstrap_rejects_traversal_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,kind in [('../escape',tarfile.REGTYPE),('config.json',tarfile.SYMTYPE)]:
                archive=root/'bad.tar.gz'
                with tarfile.open(archive,'w:gz') as tar:
                    entry=tarfile.TarInfo(name);entry.type=kind;entry.linkname='/etc/passwd';entry.size=0;tar.addfile(entry,io.BytesIO())
                with self.assertRaises(ValueError):bootstrap.extract(archive,root/'output')
                self.assertFalse((root.parent/'escape').exists())
    def test_release_gate_requires_tests_and_rejects_changed_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'verification.json').write_text(json.dumps({'passed':True,'steps':['unit']}))
            with self.assertRaisesRegex(ValueError,'Complete test receipt'):publish.check(root)
            original=publish.fingerprint
            try:
                publish.fingerprint=lambda _: {'sourceHash':'new'}
                (root/'verification.json').write_text(json.dumps({'passed':True,'steps':['unit','format','build','smoke','browser'],'browserProjects':['desktop'],'sourceHash':'old'}))
                with self.assertRaisesRegex(ValueError,'sourceHash changed'):publish.check(root)
            finally:publish.fingerprint=original
if __name__=='__main__':unittest.main()
