"""Application PDF structural limits in a disposable resource-bounded parser."""
from io import BytesIO
import subprocess
import pytest
from pypdf import PdfWriter
from api.policy import validate_policy_pdf,_PDF_LOCK,_PDF_CHILD

def pdf(pages=1,encrypted=False):
    writer=PdfWriter()
    for _ in range(pages):writer.add_blank_page(width=100,height=100)
    if encrypted:writer.encrypt('not-a-user-secret')
    stream=BytesIO();writer.write(stream);return stream.getvalue()

def test_structural_parser_accepts_one_or_bounded_multi_page_pdf():
    assert validate_policy_pdf(pdf())==1
    assert validate_policy_pdf(pdf(100))==100

@pytest.mark.parametrize('data',[b'%PDF-1.7\nmalformed',pdf(encrypted=True),pdf(101),b'not a PDF'],ids=['malformed','encrypted','over100pages','nonPDF'])
def test_malformed_encrypted_over_page_cap_or_non_pdf_rejected(data):
    with pytest.raises(ValueError,match='policy_invalid_pdf'):validate_policy_pdf(data)

def test_parser_concurrency_is_bounded():
    _PDF_LOCK.acquire()
    try:
        with pytest.raises(ValueError,match='policy_pdf_busy'):validate_policy_pdf(pdf())
    finally:_PDF_LOCK.release()

def test_timeout_kills_and_reaps_child_and_releases_parser_slot(monkeypatch):
    class Child:
        returncode=-9
        def __init__(self):self.calls=0;self.killed=False
        def communicate(self,*args,**kwargs):
            self.calls+=1
            if self.calls==1:raise subprocess.TimeoutExpired('parser',3)
            assert self.killed;return b'',b''
        def kill(self):self.killed=True
    monkeypatch.setattr('api.policy._monitor_pdf',lambda *args:None)
    Child.poll=lambda self:-9
    child=Child();monkeypatch.setattr(subprocess,'Popen',lambda *args,**kwargs:child)
    with pytest.raises(ValueError,match='policy_invalid_pdf'):validate_policy_pdf(pdf())
    assert child.killed and child.calls==2 and _PDF_LOCK.acquire(blocking=False)
    _PDF_LOCK.release()

@pytest.mark.parametrize('measurement',[None,256*1024+1])
def test_mac_watchdog_missing_measurement_or_memory_limit_kills_real_child(monkeypatch,measurement):
    import api.policy as module
    monkeypatch.setattr(module.sys,'platform','darwin')
    monkeypatch.setattr(module,'_rss_kib',lambda pid:measurement)
    children=[];create=subprocess.Popen
    def launch(*args,**kwargs):
        child=create(*args,**kwargs);children.append(child);return child
    monkeypatch.setattr(subprocess,'Popen',launch)
    with pytest.raises(ValueError,match='policy_invalid_pdf'):validate_policy_pdf(pdf())
    assert len(children)==1 and children[0].poll() is not None
    assert _PDF_LOCK.acquire(blocking=False)
    _PDF_LOCK.release()
