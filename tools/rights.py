#!/usr/bin/env python3
"""Rights and citation files for the public dataset repository and the Hugging Face card (2026-11-05).

One definition: tools/rights/rights.json (owner name, affiliation, DOI, contact). This module renders from it

  LICENSE         the notice + the full CC BY-NC 4.0 legal code (vendored: tools/rights/CC-BY-NC-4.0.legalcode.txt)
  NOTICE          what is covered and what is not
  CITATION.cff    cff-version 1.2.0, type dataset; the doi line stays a comment until zenodo_doi is a real DOI
  .zenodo.json    Zenodo's GitHub integration reads it when a GitHub release is published
  README section  "How to cite", between <!-- cite:start --> and <!-- cite:end -->
  HF card         the Hugging Face dataset card (README.md at the dataset repo root)

export_release.py calls write_all(); hf_upload_release.py calls hf_card(). `python3 tools/rights.py <dir> [release id]`
writes the files into <dir>. No rendered text may contain an e-mail address, a local path or a key (assert_clean).
Not legal advice: the wording is the owner's choice of terms, not a legal opinion.
"""
import json, re, sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
CFG = json.loads((TOOLS_DIR / 'rights' / 'rights.json').read_text())
CITE_START, CITE_END = '<!-- cite:start -->', '<!-- cite:end -->'


def is_placeholder(v):
    return str(v).startswith('{{')


def release_date(release_id):
    return release_id if re.fullmatch(r'\d{4}-\d{2}-\d{2}', release_id or '') else None


def assert_clean(text, what):
    """Refuse text that would leak an e-mail address, a local path or a key."""
    bad = [n for n, p in (('email', r'[\w.+-]+@[\w-]+\.[\w.-]+'), ('path', r'/n/fs/|/u/\w+/|/home/'), ('hf token', r'hf_[A-Za-z0-9]{20,}'),
                          ('key', r'sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}')) if re.search(p, text)]
    if bad:
        raise SystemExit(f'{what}: contains {bad}')
    return text


def doi_url():
    d = CFG['zenodo_doi']
    return d if is_placeholder(d) else 'https://doi.org/' + d


def citation(release_id):
    c = CFG
    return (f"{c['family_names']}, {c['given_names'][0]}. ({c['year']}). {c['title']} (Release {release_id}) [Data set]. "
            f"Zenodo. {doi_url()}")


def bibtex(release_id):
    c = CFG
    doi = c['zenodo_doi']
    return ("@dataset{" + "daliberti" + str(c['year']) + "csatlas,\n"
            f"  author    = {{{c['family_names']}, {c['given_names']}}},\n"
            f"  title     = {{{c['title']}}},\n"
            f"  year      = {{{c['year']}}},\n"
            f"  version   = {{{release_id}}},\n"
            "  publisher = {Zenodo},\n"
            f"  doi       = {{{doi}}},\n"
            f"  url       = {{{doi_url()}}},\n"
            f"  license   = {{{c['license_id']}}}\n}}")


def yq(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def cff(release_id):
    c = CFG
    d = release_date(release_id)
    doi = c['zenodo_doi']
    lines = ['cff-version: 1.2.0', 'message: "If you use this dataset, please cite it as below."', 'type: dataset',
             f"title: {yq(c['title'])}", 'authors:', f"  - family-names: {yq(c['family_names'])}", f"    given-names: {yq(c['given_names'])}",
             f"    affiliation: {yq(c['affiliation'])}", f"    website: {yq(c['website'])}", f"version: {yq(release_id)}"]
    if d:
        lines.append(f'date-released: {d}')
    lines += [f"license: {c['license_id']}", f"url: {yq(c['website'])}", f"repository-code: {yq(c['repo_url'])}"]
    lines.append(('# doi: ' + doi + '  (uncomment with the real DOI after the first Zenodo release)') if is_placeholder(doi) else f'doi: {yq(doi)}')
    lines.append('keywords:')
    lines += [f'  - {yq(k)}' for k in KEYWORDS]
    return '\n'.join(lines) + '\n'


KEYWORDS = ['computer science', 'research labs', 'science of science', 'bibliometrics', 'university research groups']
DESCRIPTION = ("The CS Labs Atlas: a curated, source-backed collection of computer-science PI labs, their papers and students at "
               "several universities, with a wider atlas of 300 universities. Licensed CC BY-NC 4.0; automated scraping or bulk "
               "download for AI or machine-learning training is not permitted except by permission; use this release.")


def zenodo(release_id):
    c = CFG
    z = dict(title=c['title'], upload_type='dataset', description=DESCRIPTION, version=release_id,
             creators=[dict(name=f"{c['family_names']}, {c['given_names']}", affiliation=c['affiliation'])],
             license='cc-by-nc-4.0', access_right='open', keywords=KEYWORDS,
             related_identifiers=[dict(identifier=c['repo_url'], relation='isSupplementTo', scheme='url')])
    d = release_date(release_id)
    if d:
        z['publication_date'] = d
    return json.dumps(z, ensure_ascii=False, indent=1) + '\n'


def terms():
    c = CFG
    return (f"**Terms of use.** Automated scraping or bulk download of the CS Labs Atlas website for AI or machine-learning training, "
            f"or for building datasets, is not permitted except by permission. Use the bulk data in this repository (or the "
            f"Hugging Face release) under the licence instead. The text-and-data-mining rights are expressly reserved under "
            f"Article 4(3) of EU Directive 2019/790. Commercial use needs permission: open an issue at {c['contact']}.")


def readme_section(release_id):
    c = CFG
    return (f"{CITE_START}\n## How to cite\n\n"
            f"This dataset is © {c['year']} {c['owner_name']} and licensed under [{c['license_id'].replace('CC-BY-NC-', 'CC BY-NC ')}]({c['license_url']}): "
            f"attribution is required and use is non-commercial. Papers keep their own licences. Please cite:\n\n"
            f"> {citation(release_id)}\n\n```bibtex\n{bibtex(release_id)}\n```\n\n"
            f"GitHub's \"Cite this repository\" button reads `CITATION.cff`; the DOI comes from the Zenodo record of each GitHub release.\n\n"
            f"{terms()}\n{CITE_END}\n")


def notice(release_id):
    c = CFG
    return f"""CS Labs Atlas, release {release_id}
Copyright (c) {c['year']} {c['owner_name']}

The atlas data and the site content are licensed under {c['license_name']} ({c['license_id']}):
{c['license_url']}
The full legal code is in LICENSE. Attribution is required, use is non-commercial only, and commercial use needs
the copyright holder's permission (open an issue: {c['contact']}).

COVERED by the licence and the copyright above
  - the curation of the atlas: which labs, people and papers are listed, and how they are connected
  - the compilation and selection of the data, its structure and its identifiers
  - the text, figures and analyses of the site and the documentation
  - the code in code/ (the tools that build the data), together with the data under this notice

NOT covered
  - the papers themselves: they are their authors' (or publishers') copyright and keep their own licences; the atlas
    hosts a paper's text only when it is under a Creative Commons licence or in the public domain
  - plain facts (names, titles, years, venues, identifiers) as such; the licence does not claim them, only the selection
    and arrangement of them
  - third-party sources the atlas draws on (OpenAlex, DBLP, Semantic Scholar, university pages), which keep their own terms

HOW TO CITE
  {citation(release_id)}
  See CITATION.cff and the README section "How to cite".

TERMS OF USE
  Automated scraping or bulk download of the website for AI or machine-learning training, or for building datasets,
  is not permitted except by permission. Use the bulk data from the GitHub or Hugging Face release under the licence.
  The text-and-data-mining rights are expressly reserved under Article 4(3) of EU Directive 2019/790.
"""


def license_text(release_id):
    c = CFG
    head = (f"CS Labs Atlas, release {release_id}\nCopyright (c) {c['year']} {c['owner_name']}\n\n"
            f"The atlas data and the site content are licensed under {c['license_name']}\n({c['license_id']}). "
            f"Attribution notice: credit \"{c['owner_name']}, {c['title']}\" and link {c['license_url']};\n"
            f"see NOTICE for what is and is not covered. The licence text below is the official legal code from\n"
            f"{c['license_url']}legalcode, unmodified.\n\n")
    return head + (TOOLS_DIR / 'rights' / 'CC-BY-NC-4.0.legalcode.txt').read_text()


def hf_card(release_id):
    c = CFG
    front = ("---\nlicense: cc-by-nc-4.0\npretty_name: " + c['title'] + "\ntask_categories:\n- other\nlanguage:\n- en\ntags:\n"
             "- science-of-science\n- computer-science\n- research-labs\nsize_categories:\n- 1M<n<10M\n---\n")
    body = (f"# {c['title']}\n\n{DESCRIPTION}\n\nLatest release: `{release_id}`, stored under `releases/{release_id}/`.\n\n"
            f"© {c['year']} {c['owner_name']}. Licensed under [{c['license_name']}]({c['license_url']}); see NOTICE for what is covered. "
            f"Papers keep their own licences.\n\n## Citation\n\n{citation(release_id)}\n\n```bibtex\n{bibtex(release_id)}\n```\n\n"
            f"## Terms of use\n\n{terms()}\n")
    return assert_clean(front + body, 'HF card')


def update_readme(text, release_id):
    sec = readme_section(release_id)
    if CITE_START in text and CITE_END in text:
        a, b = text.index(CITE_START), text.index(CITE_END) + len(CITE_END)
        return text[:a] + sec.rstrip('\n') + text[b:]
    return text.rstrip('\n') + '\n\n' + sec


def files(release_id):
    out = {'LICENSE': license_text(release_id), 'NOTICE': notice(release_id), 'CITATION.cff': cff(release_id), '.zenodo.json': zenodo(release_id)}
    for k, v in out.items():
        assert_clean(v, k)
    return out


def write_all(repo, release_id, record=None):
    """Write the four files into repo and refresh the README section when README.md exists; record(path, bytes) notes them."""
    repo = Path(repo)
    for name, text in files(release_id).items():
        (repo / name).write_text(text)
        if record:
            record(name, text.encode())
    rp = repo / 'README.md'
    if rp.exists():
        rp.write_text(update_readme(rp.read_text(), release_id))
    return sorted(files(release_id))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(write_all(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'development'))
