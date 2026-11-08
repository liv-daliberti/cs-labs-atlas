"""Field classification of papers for the heterogeneity analysis: theory / systems / ml_ai / other (standard library only).

Rule (fixed before any outcome was looked at): a paper's field comes from its VENUE when the venue is one of the reviewed CS venues
(hierarchy/reviewed/cs-venues.json, 548 sources) and the venue-to-area map below names an area for it; otherwise from the OpenAlex primary-topic
NAME (keyword rules), otherwise from the OpenAlex SUBFIELD default, otherwise 'other'. `field_source` records which step decided.
Definitions: theory = algorithms, complexity, combinatorics, cryptography, algorithmic game theory, learning theory; systems = computer systems
and software (architecture, OS, networking, storage, databases, distributed/cloud, security, programming languages, software engineering, EDA,
embedded); ml_ai = machine learning, vision, language, speech, AI planning/agents, data mining, retrieval; other = everything else (HCI, graphics,
robotics, signal processing and information theory, control, biology, statistics, education, general science). The alternative `field_alt` moves
robotics venues and topics from 'other' to ml_ai (a sensitivity: robotics is the largest 'other' block).
"""
import re

# (area, regex) in order; first match wins; matched against the normalised (lower-cased) venue name. 'ambiguous' sends the paper to the topic fallback.
VENUE_RULES = [
    ('ambiguous', r'^(lecture notes in computer science|proceedings|communications of the acm|society for industrial and applied mathematics ebooks|'
                  r'springer .*ebooks|science|nature|plos one|scientific reports|proceedings of the national academy of sciences|pnas|ieee access|'
                  r'journal of physics: conference series|arxiv.*|.*companion)$'),
    ('ml_ai', r'artificial intelligence and statistics|uncertainty in artificial|machine learning|learning representations|neural information|'
              r'combinatorial search|conference on language modeling|learning @ scale|nature machine intelligence'),
    ('robotics', r'robot|\bicra\b|\biros\b|automation science|intelligent vehicles|soft robotics|\brss\b|\bhri\b|ro-man|mechatronics|'
                 r'manipulat|haptic|unmanned|automation letters|autonomous robots'),
    ('theory', r'foundations of computer science|theory of computing|\bstoc\b|discrete algorithms|\bsoda\b|\bicalp\b|computational complexity|'
               r'siam journal on (computing|discrete)|journal of the acm|transactions on algorithms|combinatorial theory|innovations in theoretical|'
               r'logic in computer science|computational geometry|theoretical computer science|algorithmica|algorithms and data structures|'
               r'european symposium on algorithms|parallelism in algorithms and architectures|principles of distributed computing|'
               r'economics and computation|cryptology|\bcrypto|eurocrypt|theory of cryptography|combinatorica|random structures|journal of graph theory|'
               r'automata|quantum computing and engineering|quantum information|approximation|symposium on theoretical aspects|'
               r'principles of database systems|discrete mathematics|conference on learning theory|learning theory'),
    ('other', r'human factors|\bchi\b|user interface|\buist\b|interactive|interaction|\bcscw\b|\bdis\b|designing interactive|graphics|siggraph|'
              r'visualization|information theory|signal processing|acoustics|speech and signal|allerton|asilomar|bioinformatics|genome|biology|'
              r'\bcell\b|social network|statistic|power systems|instrumentation|optics|imaging|education|learning sciences|control systems|hybrid systems|automatica|accessibility|'
              r'mathematical programming|operations research|siam journal on optimization|probability|multimodal interaction|educational data|networked science|'
              r'collaborative learning|computer-supported|medicine|medical|clinical|neuro|physics|chemistry|materials|energy|circuits and systems for video'),
    ('ml_ai', r'artificial intelligence|\baaai\b|\bijcai\b|computer vision|pattern recognition|\bcvpr|\biccv\b|\beccv\b|\bwacv\b|3d vision|'
              r'computational linguistics|\bemnlp\b|empirical methods in natural|\bacl\b|\bnaacl\b|natural language|\bcoling\b|speech|interspeech|\bslt\b|'
              r'\basru\b|knowledge discovery|\bkdd\b|data mining|information retrieval|\bsigir\b|\bjmlr\b|autonomous agents|multi-agents|multiagent|'
              r'automated planning|\bjair\b|journal of artificial intelligence|transactions of the association for computational|multimedia|'
              r'world wide web|web conference|web search and data mining|\bwsdm\b|\bcikm\b|recommender|image processing|medical image|'
              r'web and social media|ai ethics|fairness, accountability|knowledge and data engineering|computational intelligence|'
              r'genetic and evolutionary|\bevolutionary computation|ai magazine|human language|reinforcement|conference on robot learning|pattern analysis|'
              r'face and gesture|spoken language|discourse and dialogue|machine translation|lexical and computational|language resources|representation learning|'
              r'intelligent systems and technology|text retrieval|knowledge management|user modeling'),
    ('systems', r'operating systems|\bsosp\b|\bosdi\b|networked systems design|usenix|file and storage|architectural support|computer architecture|'
                r'microarchitecture|performance computer architecture|ieee micro|\bsigcomm\b|networking|communications review|\bsigmetrics\b|'
                r'measurement and analysis of computing|internet measurement|mobile computing|wearable and ubiquitous|ubiquitous computing|\bsensys\b|'
                r'embedded|real-time systems|design automation|design, automation|computer-aided design|field-programmable|solid-state circuits|vlsi|'
                r'integrated circuits|high-performance|supercomputing|parallel and distributed|parallel processing|parallel computing|cloud computing|'
                r'symposium on cloud|data engineering|management of data|sigmod|very large data|vldb|database|data management|programming language|'
                r'\bpldi\b|\bpopl\b|sigplan|\boopsla\b|software engineering|\bicse\b|automated software|computer aided verification|formal methods|'
                r'verification|compiler|security|privacy|computer and communications security|enhancing technologies|trustworthy|blockchain|'
                r'hot topics in|computer systems|transactions on (computers|parallel|computer|dependable|mobile|embedded|storage|architecture)|'
                r'\binfocom\b|wireless|ad hoc|sensor networks|internet of things|mobile computing and communications|getmobile|'
                r'principles and practice of parallel|international symposium on (computer|microarch|high-performance)|'
                r'distributed system|distributed computing|network|mobile systems|parallel architectures|requirements engineering|software (maintenance|analysis|testing)|'
                r'mining software|reengineering|functional programming|cyber-physical|middleware|performance analysis of systems|workload characterization|'
                r'edge computing|reconfigurable|field programmable|computer design|innovative data systems|automated reasoning|software tools|journal of systems and software'),
]
TOPIC_RULES = [      # keyword rules on the OpenAlex primary-topic NAME (lower case); first match wins
    ('other', r'quantum|learning analytics|online learning and analytics|teaching and learning|e-learning|education|synchroni[sz]ation|time delay|dynamical|physic'),
    ('theory', r'complexity and algorithms|graph theory|advanced graph theory|combinatori|computability|automata|game theory|mechanism design|auction|'
               r'polynomial and algebraic|submodular|sorting|computational geometry|randomi[sz]ed|streaming algorithms|learning theory|bandit|'
               r'matrix theory and algorithms|topological and geometric data'),
    ('ml_ai', r'learning|neural|machine|topic model|natural language|language model|speech|recognition|image|vision|recommender|explainable|'
              r'adversarial|domain adaptation|gradient|generative|diffusion|attention|transformer|embedding|\btext|sentiment|dialog|semantic|'
              r'multi-agent|\bagent|bayesian|inference|prediction|classification|clustering|data mining|information retrieval|search behavior|'
              r'privacy-preserving|federated|artificial intelligence|knowledge|ontolog|\bface|video|\b3d|\bobject|detection|visual|multimodal|'
              r'fairness|\bbias|large language|chatbot|crowdsourc|anomaly'),
    ('robotics', r'robot|autonomous vehicle|manipulat|motion planning|unmanned|drone|legged|haptic|slam'),
    ('systems', r'cryptograph|database|data management|distributed|cloud|network|storage|parallel computing|embedded|real-time|hardware|security|software|'
                r'program|type systems|verification|blockchain|\biot\b|\bedge\b|operating|compiler|fault|caching|content delivery|virtuali|energy efficien|'
                r'fpga|vlsi|circuit|memory|processor|architecture|malware|intrusion|authentication|phishing|cyber|wireless|\b5g|spreadsheet|'
                r'testing|debugging|open source|\bweb\b|internet|mobile|sensing|high-performance|\bgpu|stream processing|data center'),
]
SUBFIELD_DEFAULT = {
    'Artificial Intelligence': 'ml_ai', 'Computer Vision and Pattern Recognition': 'ml_ai', 'Computer Networks and Communications': 'systems',
    'Hardware and Architecture': 'systems', 'Software': 'systems', 'Information Systems': 'systems', 'Computer Science Applications': 'other',
}
_VENUE = [(a, re.compile(p)) for a, p in VENUE_RULES]
_TOPIC = [(a, re.compile(p)) for a, p in TOPIC_RULES]
AREAS = ['theory', 'systems', 'ml_ai', 'other']


def norm_venue(v):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9@&/:,()+\- ]', ' ', (v or '').lower())).strip()


def venue_area(name):
    """Area for a venue NAME: theory/systems/ml_ai/robotics/other, 'ambiguous' (use the topic), or None when no rule fires."""
    n = norm_venue(name)
    if not n:
        return None
    for a, rx in _VENUE:
        if rx.search(n):
            return a
    return None


GATE = {'other': None, 'theory': {'Computer Science', 'Mathematics'}, 'robotics': {'Computer Science', 'Engineering'}, 'ml_ai': {'Computer Science'}, 'systems': {'Computer Science'}}


def topic_area(topic_name, subfield, field=None):
    """(area, source) from the OpenAlex primary topic: keyword rules on its name, each gated to the OpenAlex fields where the area is meant (a 'neural' topic in
    Neuroscience is not ML); then the subfield default; then 'other'. field=None skips the gate."""
    t = (topic_name or '').lower()
    for a, rx in _TOPIC:
        if t and rx.search(t) and (field is None or GATE[a] is None or field in GATE[a]):
            return a, 'topic'
    if subfield in SUBFIELD_DEFAULT and (field is None or field in {'Computer Science', 'Mathematics'}):
        return SUBFIELD_DEFAULT[subfield], 'subfield'
    return ('other', 'topic_other') if (topic_name or subfield) else (None, 'none')


def classify(venue_names, in_cs_venues, topic_name, subfield, field=None):
    """(field, field_alt, source). venue_names: names to try (lab_papers venue, OpenAlex source name); in_cs_venues: set of normalised reviewed CS venue names."""
    area = None
    for v in venue_names:
        if v and norm_venue(v) in in_cs_venues:
            area = venue_area(v)
            if area and area != 'ambiguous':
                break
    if area and area != 'ambiguous':
        src = 'venue'
    else:
        area, src = topic_area(topic_name, subfield, field)
        if area is None:
            return 'other', 'other', 'none'
    alt = 'ml_ai' if area == 'robotics' else area
    return ('other' if area == 'robotics' else area), alt, src
