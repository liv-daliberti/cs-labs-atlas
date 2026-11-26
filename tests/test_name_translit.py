from pihier.names import Name


def test_umlaut_and_dj_spellings_match_dblp_forms():
    assert Name(['Klaas Prüssmann']).match('Klaas Pruessmann')
    assert Name(['Klaas Prüssmann']).match('Klaas Prussmann')
    assert Name(['Srđan Čapkun']).match('Srdjan Capkun')
    assert Name(['Ueli Maurer']).match('Ueli Maurer') and not Name(['Ueli Maurer']).match('Ueli Mauer')
