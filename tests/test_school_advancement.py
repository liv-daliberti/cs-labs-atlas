"""Clear stage advancement preserves actual findings and dependency ordering."""
import school_closeout as C


def evaluate(failures=None):
    failures = failures or {}
    return lambda school, stage: dict(gate='fail' if int(stage) in failures else 'pass',
                                     items=failures.get(int(stage), []))


def test_student_and_paper_stages_can_progress_after_identity_without_hiding_accuracy_blockers():
    board = C.stage_board('u', evaluate({6: ['recall incomplete'], 7: ['one unexplained link'], 9: ['accuracy missing'], 10: ['not frozen']}))
    assert board['next_stage'] == 6
    assert board['stages'][6]['status'] == 'needs review'
    assert board['stages'][7]['status'] == 'needs work'
    assert board['stages'][9]['status'] == 'waiting'
    assert board['stages'][8]['gate'] == 'pass'
    assert board['stages'][8]['status'] == 'complete'    # process v4: stages 3-8 are per PI and no longer wait for each other
    assert board['stages'][9]['blocked_by'] == [6, 7]
    assert board['stages'][9]['findings'] == ['accuracy missing']
    assert not board['research_ready']


def test_early_source_failure_explains_waiting_census():
    board = C.stage_board('u', evaluate({1: ['2018 source missing'], 2: ['pending faculty']}))
    assert board['next_stage'] == 1
    assert board['stages'][2]['status'] == 'waiting'
    assert board['stages'][2]['blocked_by'] == [1]
    assert '2018 source missing' in C.render_stages(board)


def test_missing_measurement_is_unknown_instead_of_complete():
    def missing(school, stage):
        if stage == '3':
            raise FileNotFoundError('candidate register missing')
        return evaluate()(school, stage)

    board = C.stage_board('u', missing)
    assert board['stages'][3]['status'] == 'unmeasured'
    assert board['next_stage'] == 3


def test_formal_release_is_distinct_from_research_readiness_and_interim_publication():
    board = C.stage_board('u', evaluate({10: ['charter not released']}))
    assert board['research_ready'] and board['native_ready']
    assert board['next_stage'] == 10
    assert 'interim' in board['publication_note']


def test_authorized_waivers_are_visible():
    def waived(school, stage):
        return dict(gate='waived' if stage == '1' else 'pass', items=['historic gap'] if stage == '1' else [], unwaived_items=[])

    board = C.stage_board('u', waived)
    assert board['stages'][1]['status'] == 'waived'
    assert board['next_stage'] is None
