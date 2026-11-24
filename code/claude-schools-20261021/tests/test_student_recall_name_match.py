"""student_recall.name_match: nickname, hyphen and middle-name variants of one person count as recorded (legacy recall gap: 36 recorded names read as missing)."""
import student_recall as S


def test_recorded_variants_match():
    for a, b in [('Dan McGann', 'Daniel McGann'), ('Chris Klammer', 'Christopher Klammer'), ('Andy VanOsten', 'Andrew VanOsten'), ('Forest Huang', 'Forrest Huang'),
                 ('Jeeweon Jung', 'Jee-weon Jung'), ('Ozge Akmandor', 'Ayten Ozge Akmandor'), ('Zack Stier', 'Zachary Stier'), ('Phil Chodrow', 'Philip S Chodrow'),
                 ('Jackie Aslarus', 'Jacqueline Aslarus'), ('Alex Alahi', 'Alexandre Alahi'), ('Qiyang Qian', 'Qian Qiyang')]:
        assert S.name_match(a, b), (a, b)


def test_different_people_stay_apart():
    for a, b in [('Alex Lee', 'Alexa Lee'), ('Wen-Tse Chen', 'Angela Chen'), ('Eric Zhu', 'Cindy Zhu'), ('Jing Shi', 'Jiatong Shi'), ('Tianzi Wang', 'Haoran Wang'), ('Ann Lee', 'Bo Lee'),
                 ('Sam Lee', 'Samir Lee')]:
        assert not S.name_match(a, b), (a, b)
