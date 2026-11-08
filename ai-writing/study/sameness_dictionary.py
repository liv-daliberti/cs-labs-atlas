"""Curated dictionary of CS benchmarks, datasets and methods for the sameness study (measure 3), plus the matcher.

Built from data in hand, not from Papers with Code (defunct since 2025-07; nothing is scraped): (1) the OpenAlex keywords of the 47k computer-science abstracts of the study
panel and (2) a frequency list of acronyms / capitalised names mined from the same abstracts (candidate lists in sameness_bench.py `mine`), reviewed by hand; entries of
the family (ImageNet-1K, ImageNet-C, ILSVRC) are one entry. A candidate enters when its name is unambiguous in CS abstracts; ambiguous short forms (ARC, MATH, SAT, SAM,
CAN, MS) are only listed with a disambiguating word. Matching: tokens are alphanumeric runs ('CIFAR-10' = CIFAR, 10); `cs` aliases are case sensitive, `ci` aliases are not;
the last token may carry a plural 's'.

Line format: name | kind | case-sensitive aliases ; ... | case-insensitive aliases ; ...    kind: bench (evaluation suite), data (dataset / environment), meth (method, model, algorithm).
"""
import re

_TOKEN = re.compile(r'[A-Za-z0-9]+')

TABLE = r"""
ImageNet | data | ImageNet ; ILSVRC ; ImageNet-1K ; ImageNet-1k ; ImageNet-C ; ImageNet-21K ;  | tiny imagenet
CIFAR | data | CIFAR ; CIFAR-10 ; CIFAR10 ; CIFAR-100 ; CIFAR100 ; | cifar-10 ; cifar-100
MNIST | data | MNIST ; Fashion-MNIST ; EMNIST ; |
SVHN | data | SVHN ; |
COCO | data | COCO ; MS-COCO ; MSCOCO ; MS COCO ; | microsoft coco
PASCAL VOC | data | PASCAL VOC ; Pascal VOC ; VOC2012 ; VOC2007 ; |
KITTI | data | KITTI ; |
Cityscapes | data | Cityscapes ; |
ADE20K | data | ADE20K ; |
nuScenes | data | nuScenes ; |
Waymo Open | data | Waymo Open ; |
LibriSpeech | data | LibriSpeech ; Librispeech ; LibriLight ; |
Common Voice | data | Common Voice ; |
AudioSet | data | AudioSet ; |
Visual Genome | data | Visual Genome ; |
CelebA | data | CelebA ; CelebA-HQ ; FFHQ ; |
LAION | data | LAION ; LAION-5B ; |
Penn Treebank | data | Penn Treebank ; PTB ; |
WikiText | data | WikiText ; WikiText-103 ; |
Common Crawl | data | Common Crawl ; | commoncrawl
The Pile | data | The Pile ; | the pile dataset
OpenWebText | data | OpenWebText ; |
MIMIC | data | MIMIC ; MIMIC-III ; MIMIC-IV ; MIMIC-CXR ; |
UCF101 | data | UCF101 ; UCF-101 ; HMDB51 ; |
Kinetics | data | Kinetics ; Kinetics-400 ; Kinetics-600 ; |
ActivityNet | data | ActivityNet ; |
MovieLens | data | MovieLens ; |
IMDb | data | IMDb ; IMDB ; |
SNLI | data | SNLI ; MultiNLI ; MNLI ; |
CoNLL | data | CoNLL ; CoNLL-2003 ; OntoNotes ; |
WMT | data | WMT ; WMT14 ; WMT16 ; IWSLT ; |
Flickr30k | data | Flickr30k ; Flickr30K ; |
CLEVR | data | CLEVR ; |
VQA | data | VQA ; VQAv2 ; VQA v2 ; GQA ; OK-VQA ; |
ScanNet | data | ScanNet ; Matterport3D ; Habitat ; |
ShapeNet | data | ShapeNet ; ModelNet ; ModelNet40 ; |
Human3.6M | data | Human3.6M ; |
YouTube-8M | data | YouTube-8M ; |
Open Images | data | Open Images ; LVIS ; |
miniImageNet | data | miniImageNet ; Omniglot ; |
Domain adaptation sets | data | PACS ; Office-31 ; DomainNet ; Waterbirds ; |
Citation graphs | data | Cora ; Citeseer ; CiteSeer ; PubMed ; ogbn-arxiv ; |
OGB | bench | OGB ; | open graph benchmark
MoleculeNet | bench | MoleculeNet ; QM9 ; ZINC ; |
Atari | data | Atari ; ALE ; | arcade learning environment
MuJoCo | data | MuJoCo ; | openai gym
D4RL | bench | D4RL ; |
DeepMind Control | data | DeepMind Control ; DMControl ; | dm control
Meta-World | data | Meta-World ; MetaWorld ; |
Procgen | data | Procgen ; ProcGen ; |
StarCraft | data | StarCraft ; SMAC ; |
NetHack | data | NetHack ; Minecraft ; |
CARLA | data | CARLA ; |
GLUE | bench | GLUE ; SuperGLUE ; |
SQuAD | bench | SQuAD ; |
MMLU | bench | MMLU ; MMLU-Pro ; |
GSM8K | bench | GSM8K ; GSM8k ; GSM-8K ; |
MATH benchmark | bench | MATH-500 ; MATH500 ; AIME ; MATH dataset ; MATH benchmark ; | competition math
HumanEval | bench | HumanEval ; MBPP ; HumanEval+ ; |
Code benchmarks | bench | LiveCodeBench ; CodeContests ; APPS ; BigCodeBench ; Defects4J ; ClassEval ; |
SWE-bench | bench | SWE-bench ; SWE-Bench ; SWE-bench Verified ; |
BIG-bench | bench | BIG-bench ; BIG-Bench ; BBH ; |
HellaSwag | bench | HellaSwag ; WinoGrande ; PIQA ; CommonsenseQA ; OpenBookQA ; ARC-Challenge ; ARC-Easy ; |
TruthfulQA | bench | TruthfulQA ; |
GPQA | bench | GPQA ; |
Chat evals | bench | MT-Bench ; AlpacaEval ; Chatbot Arena ; Arena-Hard ; IFEval ; | chatbot arena
HELM | bench | HELM ; |
HotpotQA | bench | HotpotQA ; TriviaQA ; Natural Questions ; BoolQ ; DROP ; | natural questions
LongBench | bench | LongBench ; RULER ; Needle-in-a-Haystack ; |
MMMU | bench | MMMU ; MathVista ; MMBench ; |
Agent benchmarks | bench | WebArena ; AgentBench ; ALFWorld ; ToolBench ; OSWorld ; |
Summarization sets | data | XSum ; CNN/DailyMail ; |
TPC | bench | TPC-H ; TPC-DS ; TPC-C ; |
YCSB | bench | YCSB ; |
SPEC CPU | bench | SPEC CPU ; SPEC2006 ; SPEC CPU2017 ; PARSEC ; MLPerf ; Rodinia ; PolyBench ; |
Transformer | meth | Transformer ; Transformers ; | transformer architecture ; transformer model ; self-attention
BERT | meth | BERT ; RoBERTa ; DistilBERT ; ALBERT ; |
GPT-2/3 | meth | GPT-2 ; GPT-3 ; GPT-3.5 ; GPT2 ; GPT3 ; |
GPT-4 | meth | GPT-4 ; GPT-4o ; GPT-4V ; GPT4 ; GPT-5 ; o1 ; o3 ; |
ChatGPT | meth | ChatGPT ; |
LLaMA | meth | LLaMA ; Llama ; Llama-2 ; Llama-3 ; LLaMA-2 ; LLaMA-3 ; Llama 2 ; Llama 3 ; Vicuna ; Alpaca ; |
Qwen | meth | Qwen ; Qwen2 ; Qwen2.5 ; Qwen3 ; |
Mistral | meth | Mistral ; Mixtral ; |
Gemini | meth | Gemini ; Gemma ; PaLM ; |
Claude | meth | Claude ; |
DeepSeek | meth | DeepSeek ; DeepSeek-R1 ; DeepSeek-V3 ; |
T5 | meth | T5 ; BART ; Flan-T5 ; |
CLIP | meth | CLIP ; SigLIP ; |
Vision Transformer | meth | ViT ; ViTs ; | vision transformer
ResNet | meth | ResNet ; ResNet-50 ; ResNet50 ; ResNet-18 ; ResNets ; |
VGG | meth | VGG ; VGG16 ; VGG-16 ; AlexNet ; GoogLeNet ; DenseNet ; EfficientNet ; MobileNet ; |
U-Net | meth | U-Net ; UNet ; |
YOLO | meth | YOLO ; Faster R-CNN ; Mask R-CNN ; DETR ; RetinaNet ; |
SAM | meth | Segment Anything ; | segment anything
Diffusion models | meth | DDPM ; DDIM ; Stable Diffusion ; | diffusion model ; diffusion models ; denoising diffusion ; latent diffusion ; flow matching
GAN | meth | GAN ; GANs ; StyleGAN ; CycleGAN ; | generative adversarial network
VAE | meth | VAE ; VAEs ; | variational autoencoder
LSTM / GRU | meth | LSTM ; LSTMs ; GRU ; GRUs ; | long short-term memory
RNN | meth | RNN ; RNNs ; | recurrent neural network
CNN | meth | CNN ; CNNs ; ConvNet ; ConvNets ; | convolutional neural network
GNN | meth | GNN ; GNNs ; GCN ; GCNs ; GAT ; GraphSAGE ; | graph neural network ; graph convolutional
MLP | meth | MLP ; MLPs ; | multilayer perceptron ; multi-layer perceptron
Mixture of experts | meth | MoE ; | mixture of experts ; mixture-of-experts
State-space sequence models | meth | Mamba ; S4 ; | structured state space ; selective state space ; state space sequence
Parameter-efficient fine-tuning | meth | LoRA ; QLoRA ; | low-rank adaptation ; parameter-efficient fine-tuning
RLHF | meth | RLHF ; RLAIF ; | reinforcement learning from human feedback
DPO | meth | DPO ; | direct preference optimization ; preference optimization
PPO | meth | PPO ; TRPO ; | proximal policy optimization
GRPO | meth | GRPO ; RLVR ; |
Supervised fine-tuning | meth | SFT ; | supervised fine-tuning ; instruction tuning ; instruction-tuned
Chain of thought | meth | CoT ; | chain-of-thought ; chain of thought
In-context learning | meth | ICL ; | in-context learning ; few-shot prompting ; prompt engineering
RAG | meth | RAG ; | retrieval-augmented generation ; retrieval augmented generation
Knowledge distillation | meth | | knowledge distillation ; model distillation
Contrastive learning | meth | SimCLR ; MoCo ; InfoNCE ; | contrastive learning ; contrastive loss
Self-supervised learning | meth | BYOL ; DINO ; MAE ; | self-supervised learning ; self-supervised pre-training ; masked autoencoder
Adam | meth | Adam ; AdamW ; | adam optimizer
SGD | meth | SGD ; | stochastic gradient descent ; gradient descent
Normalization and dropout | meth | | batch normalization ; layer normalization ; dropout
Word embeddings | meth | word2vec ; Word2Vec ; GloVe ; | word embeddings
Deep RL algorithms | meth | DQN ; A3C ; SAC ; DDPG ; TD3 ; | deep q-network ; q-learning ; actor-critic ; policy gradient
MCTS | meth | MCTS ; AlphaGo ; AlphaZero ; MuZero ; | monte carlo tree search
AlphaFold | meth | AlphaFold ; AlphaFold2 ; |
Gaussian process | meth | | gaussian process ; gaussian processes
SVM | meth | SVM ; SVMs ; | support vector machine
Tree ensembles | meth | XGBoost ; LightGBM ; | random forest ; gradient boosting ; decision tree
k-means | meth | | k-means ; kmeans
PCA | meth | PCA ; t-SNE ; UMAP ; | principal component analysis
Topic model | meth | LDA ; | latent dirichlet allocation ; topic model
HMM / CRF | meth | HMM ; CRF ; | hidden markov model ; conditional random field
Bayesian optimization | meth | | bayesian optimization
ADMM | meth | ADMM ; | alternating direction method of multipliers
Frank-Wolfe | meth | | frank-wolfe
Variance reduction | meth | SVRG ; SARAH ; |
Federated learning | meth | FedAvg ; FedProx ; | federated learning
Differential privacy | meth | DP-SGD ; | differential privacy
Meta-learning | meth | MAML ; | meta-learning ; meta learning
Neural architecture search | meth | NAS ; | neural architecture search
NeRF | meth | NeRF ; NeRFs ; | neural radiance field ; gaussian splatting
SLAM | meth | SLAM ; | simultaneous localization and mapping
Sampling planners | meth | RRT ; RRT* ; PRM ; | sampling-based motion planning
Model predictive control | meth | MPC ; | model predictive control
LQR | meth | LQR ; | linear quadratic regulator
Control barrier functions | meth | CBF ; CBFs ; | control barrier function
SAT/SMT solving | meth | Z3 ; SMT ; | smt solver ; sat solver ; satisfiability modulo theories
Mathematical programming | meth | MILP ; | mixed-integer linear programming ; integer linear programming ; semidefinite programming ; linear programming
MCMC | meth | MCMC ; | markov chain monte carlo ; variational inference
Multi-armed bandits | meth | UCB ; | multi-armed bandit ; thompson sampling
Neural tangent kernel | meth | NTK ; | neural tangent kernel
Conformal prediction | meth | | conformal prediction
Optimal transport | meth | | optimal transport ; wasserstein distance
Neural scaling laws | meth | | neural scaling laws ; scaling laws for language ; compute-optimal
Agents | meth | ReAct ; | llm agents ; language agents ; tool use
MapReduce / Spark | meth | MapReduce ; Spark ; Hadoop ; | apache spark
Consensus protocols | meth | Raft ; Paxos ; PBFT ; | byzantine fault tolerance
Key-value stores | meth | RocksDB ; LevelDB ; Redis ; |
LLVM | meth | LLVM ; MLIR ; |
CUDA | meth | CUDA ; Triton ; OpenMP ; MPI ; OpenCL ; |
Deep-learning frameworks | meth | PyTorch ; TensorFlow ; JAX ; |
Homomorphic encryption | meth | FHE ; | homomorphic encryption ; zero-knowledge proof
SGX / TEEs | meth | SGX ; TEE ; TEEs ; | trusted execution environment
"""


def parse():
    ents = []
    for line in TABLE.strip().splitlines():
        parts = [x.strip() for x in line.split('|')]
        name, kind = parts[0], parts[1]
        cs = [a.strip() for a in parts[2].split(';') if a.strip()] if len(parts) > 2 else []
        ci = [a.strip() for a in parts[3].split(';') if a.strip()] if len(parts) > 3 else []
        ents.append(dict(name=name, kind=kind, cs=cs, ci=ci))
    return ents


def toks(s):
    return _TOKEN.findall(s)


class Matcher:
    """Presence of dictionary entries in a text. Case-sensitive aliases match the tokens as written; case-insensitive aliases match lower-cased tokens."""

    def __init__(self, ents=None):
        self.ents = ents or parse()
        self.names = [e['name'] for e in self.ents]
        self.kinds = [e['kind'] for e in self.ents]
        self.cs, self.ci = {}, {}
        for i, e in enumerate(self.ents):
            for a in e['cs']:
                t = tuple(toks(a))
                if t:
                    self.cs.setdefault(t[0], []).append((t, i))
            for a in e['ci']:
                t = tuple(x.lower() for x in toks(a))
                if t:
                    self.ci.setdefault(t[0], []).append((t, i))

    @staticmethod
    def _eq(seq, t):
        n = len(t)
        if len(seq) < n:
            return False
        if n > 1 and any(seq[j] != t[j] for j in range(n - 1)):
            return False
        return seq[n - 1] == t[n - 1] or seq[n - 1] == t[n - 1] + 's'

    def hits(self, text):
        """[(entry index, start char, end char)] of every occurrence in text."""
        sp = [(m.start(), m.end()) for m in _TOKEN.finditer(text)]
        tk = [text[a:b] for a, b in sp]
        lw = [x.lower() for x in tk]
        seen = {}
        cs, ci = self.cs, self.ci
        for pos in range(len(tk)):
            for table, seq in ((cs.get(tk[pos]), tk), (ci.get(lw[pos]), lw)):
                for t, i in table or ():
                    if self._eq(seq[pos:pos + len(t)], t):
                        seen.setdefault((pos, i), (sp[pos][0], sp[min(pos + len(t), len(sp)) - 1][1]))
                        break
        return [(i, a, b) for (pos, i), (a, b) in sorted(seen.items())]

    def counts(self, text):
        """{entry index: number of occurrences} in text."""
        out = {}
        for i, _, _ in self.hits(text):
            out[i] = out.get(i, 0) + 1
        return out
