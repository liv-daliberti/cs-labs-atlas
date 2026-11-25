import cornell_ecommons as E


def test_records_take_chair_then_advisor_and_year():
    doc = {'_embedded': {'searchResult': {'page': {'totalPages': 1}, '_embedded': {'objects': [
        {'_embedded': {'indexableObject': {'handle': '1813/117426', 'name': 'T1', 'metadata': {
            'dc.contributor.author': [{'value': 'Fassman, Ellie'}], 'dc.contributor.chair': [{'value': 'Stephens-Davidowitz, Noah'}],
            'dc.contributor.committeeMember': [{'value': 'Kleinberg, Robert'}], 'dc.date.issued': [{'value': '2025-05'}],
            'thesis.degree.discipline': [{'value': 'Computer Science'}], 'thesis.degree.level': [{'value': 'Doctor of Philosophy'}]}}}},
        {'_embedded': {'indexableObject': {'handle': '1813/1', 'name': 'T2', 'metadata': {
            'dc.contributor.author': [{'value': 'X, Y'}], 'dc.contributor.advisor': [{'value': 'Messer, Phillip'}], 'dc.date.issued': [{'value': '2017'}]}}}}]}}}}
    rows = E.records(doc, 'u', 's')
    assert rows[0]['chair'] == ['Stephens-Davidowitz, Noah'] and rows[0]['year'] == 2025 and rows[0]['committee'] == ['Kleinberg, Robert']
    assert rows[1]['chair'] == ['Messer, Phillip'] and rows[1]['chair_field'] == 'dc.contributor.advisor'
