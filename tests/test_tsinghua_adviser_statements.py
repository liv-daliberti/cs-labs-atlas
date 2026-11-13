"""Tsinghua adviser statements in department pages, the Beijing outstanding-thesis list and PI profile pages (tools/tsinghua_adviser_statements.py, R-STU-30)."""
import datetime as dt
import hashlib

import tsinghua_adviser_statements as T

PIS = [dict(pi='艾清遥', names=['Qingyao Ai'], departments=['CS'], periods=[dict(start='2022', end=None)]),
       dict(pi='李越', names=[], departments=['EE'], periods=[]),
       dict(pi='李勇', names=[], departments=['EE'], periods=[]),
       dict(pi='李勇 [CS]', names=[], departments=['CS'], periods=[dict(start='2016', end=None)]),
       dict(pi='王斌', names=[], departments=['SW'], periods=[dict(start='2016', end=None)]),
       dict(pi='王斌 [CS]', names=[], departments=['CS'], periods=[dict(start='2016', end=None)]),
       dict(pi='姜宇', names=[], departments=['SW'], periods=[dict(start='2016', end=None)]),
       dict(pi='刘奕群', names=[], departments=['CS'], periods=[dict(start='2012-12', end=None)])]
PERIODS = [dict(name='李越', facultyStart='2021', facultyEnd=None)]
TODAY = dt.date(2026, 11, 13)


def page(body, date='2024.08.28'):
    return f'<html><body><h5>T</h5><p>正文 标题 {date} 13:16</p><p>{body}</p></body></html>'.encode()


def cap(url, raw):
    return dict(url=url, sha256=hashlib.sha256(raw).hexdigest(), raw=raw)


def run(*caps, periods=PERIODS):
    return T.evidence(list(caps), PIS, periods, today=TODAY)


CS = 'https://www.cs.tsinghua.edu.cn/info/1058/1.htm'
EE = 'https://www.ee.tsinghua.edu.cn/info/1445/1.htm'


def students(rows):
    return {(r['pi'], s['name']): s for r in rows for s in r['students']}


def test_R_STU_30_news_statement_is_a_dated_phd_row_with_a_verbatim_quote():
    raw = page('我是计算机系2026级直博生钟羿，导师是艾清遥副教授。今天', date='2026.08.30')
    rows, held, counts = run(cap(CS, raw))
    s = students(rows)[('艾清遥', '钟羿')]
    assert s['role'] == 'phd' and s['years'] == [2026, 2026] and s['quote'] in T.flat(raw.decode()) and s['sha256'] == hashlib.sha256(raw).hexdigest()


def test_R_STU_30_patterns_masters_graduate_and_thesis_sentence():
    raw = page('关超宇，计算机系2019级硕士研究生，导师艾清遥教授。叶子逸，2016年考入清华，2020年进入计算机系攻读博士学位，导师为艾清遥教授。'
               '软件学院2024届博士毕业生罗正雄的博士学位论文《某某》获奖，指导教师为软件学院艾清遥副教授。', date='2023.05.01')
    got = students(run(cap(CS, raw))[0])
    assert got[('艾清遥', '关超宇')]['role'] == 'masters' and ('艾清遥', '叶子逸') in got and got[('艾清遥', '罗正雄')]['role'] == 'phd'


def test_R_STU_30_garbled_names_competition_teams_and_unspecified_levels_are_not_rows():
    raw = page('止有定，深耕致远——在级研究生开学典礼上的发言 随后，博士生导师艾清遥、各位。作者：计算机系硕士生方言、博士生詹靖涛等，指导教师：艾清遥助理教授。'
               '黄锴宇，论文第一作者，博士后，合作导师是艾清遥教授。')
    rows, held, counts = run(cap(CS, raw))
    assert rows == [] and counts['rows'] == 0


def test_R_STU_30_adviser_must_be_exactly_one_pi_and_the_site_must_match_the_department():
    other = page('钟羿，计算机系博士生，导师是王斌教授。', date='2023.01.01')
    rows, held, _ = run(cap(CS, other))
    assert rows == [] and held[0]['held_reason'] == 'adviser_not_one_pi'   # 王斌 is two PIs: dropped
    rows, held, _ = run(cap(EE, page('钟羿，博士生，导师是艾清遥教授。')))
    assert rows == [] and held[0]['held_reason'] == 'page_site_not_pi_department'


def test_R_STU_30_a_tagged_pi_name_matches_only_its_departments_site():
    rows, held, _ = run(cap(CS, page('孙豪，计算机系博士生，导师是李勇教授。')))
    assert rows == [] and held[0]['held_reason'] == 'adviser_not_one_pi'   # 李勇 and 李勇 [CS] share the Han name: dropped, never guessed


def test_R_STU_30_period_is_required_and_the_year_must_lie_inside_it():
    raw = page('秦岭，电子系博士生，导师李越老师。', date='2023.05.01')
    assert students(run(cap(EE, raw))[0])[('李越', '秦岭')]['years'] == [2023, 2023]
    rows, held, _ = run(cap(EE, raw), periods=[])
    assert rows == [] and held[0]['held_reason'] == 'no_period_record'
    rows, held, _ = run(cap(EE, page('秦岭，电子系博士生，导师李越老师。', date='2018.05.01')))
    assert rows == [] and held[0]['held_reason'].startswith('year_2018_outside_period_2021')


def test_R_STU_30_future_dated_page_and_missing_date_are_held():
    rows, held, _ = run(cap(CS, page('钟羿，计算机系博士生，导师是艾清遥教授。', date='2027.02.01')))
    assert rows == [] and held[0]['held_reason'] == 'year_outside_window_or_future'
    raw = b'<html><body><p>\xe9\x92\x9f\xe7\xbe\xbf\xef\xbc\x8c\xe5\x8d\x9a\xe5\xa3\xab\xe7\x94\x9f\xef\xbc\x8c\xe5\xaf\xbc\xe5\xb8\x88\xe6\x98\xaf\xe8\x89\xbe\xe6\xb8\x85\xe9\x81\xa5\xe6\x95\x99\xe6\x8e\x88</p></body></html>'
    rows, held, _ = run(cap(CS, raw))
    assert rows == [] and held[0]['held_reason'] == 'year_outside_window_or_future'


def test_R_STU_30_a_capture_whose_sha_does_not_match_is_ignored():
    raw = page('钟羿，计算机系博士生，导师是艾清遥教授。')
    c = cap(CS, raw)
    c['sha256'] = '0' * 64
    assert run(c)[2]['pages'] == 0


def test_R_STU_30_thesis_list_line_is_the_award_year_and_a_nomination_still_counts(monkeypatch):
    lines = ['2023   计算机科学与技术   裘捷中   刘奕群   图表示学习的谱理论与自监督学习   提名', '2013   计算机科学与技术   程明明   刘奕群   旧论文',
             '2024   机械工程   王嘉伟   艾清遥   不匹配学科']
    monkeypatch.setattr(T, 'pdf_text', lambda raw: '\n'.join(lines))
    raw = b'%PDF-fake'
    rows, held, _ = run(cap('https://www.tsinghua.edu.cn/x/list.pdf', raw))
    s = students(rows)[('刘奕群', '裘捷中')]
    assert s['years'] == [2023, 2023] and s['source_class'].endswith('_nomination')
    why = {h['student']: h['held_reason'] for h in held}
    assert why['程明明'] == 'year_outside_window_or_future' and why['王嘉伟'] == 'page_site_not_pi_department'


def test_R_STU_30_profile_page_dated_by_the_stated_year_and_owned_by_one_pi():
    raw = page('刘奕群 清华大学教授 2018年指导博士生曾锦乐获Henry Granjon Award。')
    rows, held, _ = run(cap('https://www.cs.tsinghua.edu.cn/info/1106/1.htm', raw))
    assert students(rows)[('刘奕群', '曾锦乐')]['years'] == [2018, 2018]
