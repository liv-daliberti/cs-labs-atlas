from stage_gate import mixed_author_exclusions


def test_mixed_author_exclusion_requires_exact_id_names_and_non_pi_review():
    mixed = {'author': 'https://openalex.org/A1', 'name': 'Daniel Thalmann',
             'names': ['Daniel Thalmann', 'Nadia Magnenat Thalmann']}
    clean = {'author': 'https://openalex.org/A2', 'name': 'Daniel Thalmann', 'names': ['Daniel Thalmann']}
    review = {
        'decisions': [{'name': 'Daniel Thalmann', 'openalex': [mixed['author']], 'decision': 'faculty_no_pi_evidence'}],
        'mixed_author_exclusions': [{
            'author': mixed['author'], 'candidate_names': mixed['names'], 'reason': 'two separate coauthors mixed by index',
            'evidence': [{'url': 'https://publisher.example/paper', 'sha256': 'a' * 64,
                          'quote': 'Nadia Magnenat Thalmann and Daniel Thalmann'}],
        }],
    }
    assert mixed_author_exclusions([mixed, clean], review) == ({mixed['author']}, [])

    review['mixed_author_exclusions'][0]['candidate_names'] = ['Daniel Thalmann']
    assert mixed_author_exclusions([mixed, clean], review)[0] == set()
    review['mixed_author_exclusions'][0]['candidate_names'] = mixed['names']
    review['decisions'][0]['decision'] = 'accepted'
    assert mixed_author_exclusions([mixed, clean], review)[0] == set()
