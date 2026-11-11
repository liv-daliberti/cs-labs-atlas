import listing_formats as F


def test_legacy_directory_excludes_blank_templates_and_ambiguous_ranks():
    html = '''<div class="j_name_num"><dd class="j_name"><span class="name"><a href="view.php?aid=1">张明</a></span><span class="job_name">副教授</span></dd></div>
      <div class="j_name_num"><dd class="j_name"><span class="name"><a href="view.php?aid=2"></a></span><span class="job_name">教授</span></dd></div>
      <div class="j_name_num"><dd class="j_name"><span class="name"><a href="view.php?aid=3">Visitor</a></span><span class="job_name">教授,副教授,讲师</span></dd></div>'''
    assert F.whu_cs_legacy(html) == [dict(name_listed='张明', titles=['副教授'],
                                          homepage=None, division=None, profile='view.php?aid=1')]


def test_current_faculty_and_talents_use_printed_ranks_only():
    main = '<div class="teacher-list-item"><ul class="li-xinxi"><li><div class="name"><a href="/pi">李华</a></div><div class="sex">女</div><div class="zhichen">教授</div></li></ul></div>'
    talent = '<div class="talent-item"><ul><li><a href="/talent"><div class="title">王强</div><div class="technical">研究员</div></a></li></ul></div>'
    assert F.whu_cs_zrjs(main)[0]['titles'] == ['教授']
    assert F.whu_cs_talents(talent)[0]['titles'] == ['研究员']
    assert len(F.whu_cs_zrjs(talent)) == 0


def test_emeritus_category_does_not_invent_a_profile():
    html = '<div class="teacher-list honored"><div class="teacher-list-item"><ul><li><a href="javascript:void(0)">陈老师</a></li></ul></div></div>'
    assert F.whu_cs_emeritus(html) == [dict(name_listed='陈老师', titles=['退休教师'],
                                            homepage=None, division=None, profile=None)]
