from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = REPO_ROOT / "rules" / "cgel_retagging.csv"
RETAG_SCRIPT = REPO_ROOT / "scripts" / "retag.py"
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit.py"

SAMPLE_CONLLU = """# sent_id = s1
# text = This helps.
1\tThis\tthis\tPRON\tDT\tNumber=Sing|PronType=Dem\t2\tnsubj\t2:nsubj\t_
2\thelps\thelp\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s2
# text = The idea that worked surprised us.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\tidea\tidea\tNOUN\tNN\tNumber=Sing\t5\tnsubj\t5:nsubj\t_
3\tthat\tthat\tPRON\tWDT\tPronType=Rel\t4\tnsubj\t4:nsubj\t_
4\tworked\twork\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t2\tacl:relcl\t2:acl:relcl\t_
5\tsurprised\tsurprise\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
6\tus\twe\tPRON\tPRP\tCase=Acc|Number=Plur|Person=1|PronType=Prs\t5\tobj\t5:obj\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t5\tpunct\t5:punct\t_

# sent_id = s3
# text = What do we get?
1\tWhat\twhat\tPRON\tWP\tPronType=Int\t4\tobj\t4:obj\t_
2\tdo\tdo\tAUX\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t4\taux\t4:aux\t_
3\twe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t4\tnsubj\t4:nsubj\t_
4\tget\tget\tVERB\tVB\tVerbForm=Inf\t0\troot\t0:root\tSpaceAfter=No
5\t?\t?\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s4
# text = There is hope.
1\tThere\tthere\tPRON\tEX\t_\t2\texpl\t2:expl\t_
2\tis\tbe\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\t_
3\thope\thope\tNOUN\tNN\tNumber=Sing\t2\tnsubj\t2:nsubj\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s5
# text = Because it rained.
1\tBecause\tbecause\tSCONJ\tIN\t_\t3\tmark\t3:mark\t_
2\tit\tit\tPRON\tPRP\tCase=Nom|Number=Sing|Person=3|PronType=Prs\t3\tnsubj\t3:nsubj\t_
3\trained\train\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s6
# text = Whatever works.
1\tWhatever\twhatever\tPRON\tWP\tPronType=Int\t2\tnsubj\t2:nsubj\t_
2\tworks\twork\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s7
# text = Stay here.
1\tStay\tstay\tVERB\tVB\tVerbForm=Inf\t0\troot\t0:root\t_
2\there\there\tADV\tRB\tPronType=Dem\t1\tadvmod\t1:advmod\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s8
# text = We want to leave.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\twant\twant\tVERB\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\t_
3\tto\tto\tPART\tTO\t_\t4\tmark\t4:mark\t_
4\tleave\tleave\tVERB\tVB\tVerbForm=Inf\t2\txcomp\t2:xcomp\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s9
# text = For Kim to leave matters.
1\tFor\tfor\tSCONJ\tIN\t_\t4\tmark\t4:mark\t_
2\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
3\tto\tto\tPART\tTO\t_\t4\tmark\t4:mark\t_
4\tleave\tleave\tVERB\tVB\tVerbForm=Inf\t5\tcsubj\t5:csubj\t_
5\tmatters\tmatter\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t5\tpunct\t5:punct\t_

# sent_id = s10
# text = Thanks for thinking.
1\tThanks\tthanks\tNOUN\tNN\tNumber=Sing\t0\troot\t0:root\t_
2\tfor\tfor\tSCONJ\tIN\t_\t3\tmark\t3:mark\t_
3\tthinking\tthink\tVERB\tVBG\tVerbForm=Ger\t1\tacl\t1:acl:for\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s11
# text = Kim and Pat left.
1\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
2\tand\tand\tCCONJ\tCC\t_\t3\tcc\t3:cc\t_
3\tPat\tPat\tPROPN\tNNP\tNumber=Sing\t1\tconj\t1:conj\t_
4\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s12
# text = Kim as well as Pat left.
1\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t6\tnsubj\t6:nsubj\t_
2\tas\tas\tADV\tRB\tExtPos=CCONJ\t5\tcc\t5:cc\t_
3\twell\twell\tADV\tRB\tDegree=Pos\t2\tfixed\t2:fixed\t_
4\tas\tas\tADP\tIN\t_\t2\tfixed\t2:fixed\t_
5\tPat\tPat\tPROPN\tNNP\tNumber=Sing\t1\tconj\t1:conj\t_
6\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t6\tpunct\t6:punct\t_

# sent_id = s13
# text = Blog/site helps.
1\tBlog\tblog\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
2\t/\t/\tSYM\tSYM\t_\t3\tcc\t3:cc\t_
3\tsite\tsite\tNOUN\tNN\tNumber=Sing\t1\tconj\t1:conj\t_
4\thelps\thelp\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s14
# text = We don't leave.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t4\tnsubj\t4:nsubj\t_
2\tdo\tdo\tAUX\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t4\taux\t4:aux\t_
3\tn't\tnot\tPART\tRB\tPolarity=Neg\t4\tadvmod\t4:advmod\t_
4\tleave\tleave\tVERB\tVB\tVerbForm=Inf\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s15
# text = Three books arrived.
1\tThree\tthree\tNUM\tCD\tNumForm=Word|NumType=Card\t2\tnummod\t2:nummod\t_
2\tbooks\tbook\tNOUN\tNNS\tNumber=Plur\t3\tnsubj\t3:nsubj\t_
3\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s16
# text = Two hundred people arrived.
1\tTwo\ttwo\tNUM\tCD\tNumForm=Word|NumType=Card\t2\tcompound\t2:compound\t_
2\thundred\thundred\tNUM\tCD\tNumForm=Word|NumType=Card\t3\tnummod\t3:nummod\t_
3\tpeople\tpeople\tNOUN\tNNS\tNumber=Plur\t4\tnsubj\t4:nsubj\t_
4\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s17
# text = Three arrived.
1\tThree\tthree\tNUM\tCD\tNumForm=Word|NumType=Card\t2\tnsubj\t2:nsubj\t_
2\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s18
# text = The third book arrived.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t3\tdet\t3:det\t_
2\tthird\tthird\tADJ\tJJ\tDegree=Pos|NumForm=Word|NumType=Ord\t3\tamod\t3:amod\t_
3\tbook\tbook\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
4\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s19
# text = No one objected.
1\tNo\tno\tDET\tDT\tPronType=Neg\t2\tdet\t2:det\t_
2\tone\tone\tPRON\tNN\tNumber=Sing|PronType=Neg\t3\tnsubj\t3:nsubj\t_
3\tobjected\tobject\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s20
# text = They spoke to one another.
1\tThey\tthey\tPRON\tPRP\tCase=Nom|Number=Plur|Person=3|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tspoke\tspeak\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tto\tto\tADP\tIN\t_\t4\tcase\t4:case\t_
4\tone\tone\tPRON\tCD\tExtPos=PRON|PronType=Rcp\t2\tobl\t2:obl:to\t_
5\tanother\tanother\tDET\tDT\tPronType=Ind\t4\tfixed\t4:fixed\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s21
# text = Say that Kim left.
1\tSay\tsay\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\tthat\tthat\tSCONJ\tIN\t_\t4\tmark\t4:mark\t_
3\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
4\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t1\tccomp\t1:ccomp\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s22
# text = Ask whether Kim left.
1\tAsk\task\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\twhether\twhether\tSCONJ\tIN\t_\t4\tmark\t4:mark\t_
3\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
4\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t1\tccomp\t1:ccomp\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s23
# text = Both Kim and Pat left.
1\tBoth\tboth\tCCONJ\tCC\t_\t2\tcc:preconj\t2:cc:preconj\t_
2\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t5\tnsubj\t5:nsubj\t_
3\tand\tand\tCCONJ\tCC\t_\t4\tcc\t4:cc\t_
4\tPat\tPat\tPROPN\tNNP\tNumber=Sing\t2\tconj\t2:conj:and|5:nsubj\t_
5\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t5\tpunct\t5:punct\t_

# sent_id = s24
# text = They were both ready.
1\tThey\tthey\tPRON\tPRP\tCase=Nom|Number=Plur|Person=3|PronType=Prs\t4\tnsubj\t4:nsubj\t_
2\twere\tbe\tAUX\tVBD\tMood=Ind|Number=Plur|Person=3|Tense=Past|VerbForm=Fin\t4\tcop\t4:cop\t_
3\tboth\tboth\tADV\tRB\t_\t4\tadvmod\t4:advmod\t_
4\tready\tready\tADJ\tJJ\tDegree=Pos\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s25
# text = Ask if Kim left.
1\tAsk\task\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\tif\tif\tSCONJ\tIN\t_\t4\tmark\t4:mark\t_
3\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
4\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t1\tccomp\t1:ccomp\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s26
# text = If Kim left, call Pat.
1\tIf\tif\tSCONJ\tIN\t_\t3\tmark\t3:mark\t_
2\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t3\tnsubj\t3:nsubj\t_
3\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t5\tadvcl\t5:advcl\t_
4\t,\t,\tPUNCT\t,\t_\t3\tpunct\t3:punct\t_
5\tcall\tcall\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
6\tPat\tPat\tPROPN\tNNP\tNumber=Sing\t5\tobj\t5:obj\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t5\tpunct\t5:punct\t_

# sent_id = s27
# text = Kim along with Pat left.
1\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t5\tnsubj\t5:nsubj\t_
2\talong\talong\tADP\tIN\t_\t4\tcase\t4:case\t_
3\twith\twith\tADP\tIN\t_\t4\tcase\t4:case\t_
4\tPat\tPat\tPROPN\tNNP\tNumber=Sing\t1\tnmod\t1:nmod\t_
5\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t5\tpunct\t5:punct\t_

# sent_id = s28
# text = We whispered so Kim could sleep.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\twhispered\twhisper\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tso\tso\tSCONJ\tIN\t_\t6\tmark\t6:mark\t_
4\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t6\tnsubj\t6:nsubj\t_
5\tcould\tcould\tAUX\tMD\tVerbForm=Fin\t6\taux\t6:aux\t_
6\tsleep\tsleep\tVERB\tVB\tVerbForm=Inf\t2\tadvcl\t2:advcl\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s29
# text = I asked if Kim left or if Pat stayed.
1\tI\tI\tPRON\tPRP\tCase=Nom|Number=Sing|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tasked\task\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tif\tif\tSCONJ\tIN\t_\t5\tmark\t5:mark\t_
4\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t5\tnsubj\t5:nsubj\t_
5\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t2\tccomp\t2:ccomp\t_
6\tor\tor\tCCONJ\tCC\t_\t9\tcc\t9:cc\t_
7\tif\tif\tSCONJ\tIN\t_\t9\tmark\t9:mark\t_
8\tPat\tPat\tPROPN\tNNP\tNumber=Sing\t9\tnsubj\t9:nsubj\t_
9\tstayed\tstay\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t5\tconj\t5:conj:or|2:ccomp\tSpaceAfter=No
10\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s30
# text = Kim tried, yet Pat stayed.
1\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t2\tnsubj\t2:nsubj\t_
2\ttried\ttry\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
3\t,\t,\tPUNCT\t,\t_\t2\tpunct\t2:punct\t_
4\tyet\tyet\tCCONJ\tCC\t_\t6\tcc\t6:cc\t_
5\tPat\tPat\tPROPN\tNNP\tNumber=Sing\t6\tnsubj\t6:nsubj\t_
6\tstayed\tstay\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t2\tconj\t2:conj:yet\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s31
# text = Kim chose tea rather than coffee.
1\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t2\tnsubj\t2:nsubj\t_
2\tchose\tchoose\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\ttea\ttea\tNOUN\tNN\tNumber=Sing\t2\tobj\t2:obj\t_
4\trather\trather\tADV\tRB\tExtPos=CCONJ\t6\tcc\t6:cc\t_
5\tthan\tthan\tADP\tIN\t_\t4\tfixed\t4:fixed\t_
6\tcoffee\tcoffee\tNOUN\tNN\tNumber=Sing\t3\tconj\t3:conj:rather_than\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s32
# text = Rather than waiting, Kim left.
1\tRather\trather\tADV\tRB\tExtPos=SCONJ\t3\tmark\t3:mark\t_
2\tthan\tthan\tSCONJ\tIN\t_\t1\tfixed\t1:fixed\t_
3\twaiting\twait\tVERB\tVBG\tVerbForm=Ger\t6\tadvcl\t6:advcl:rather_than\t_
4\t,\t,\tPUNCT\t,\t_\t3\tpunct\t3:punct\t_
5\tKim\tKim\tPROPN\tNNP\tNumber=Sing\t6\tnsubj\t6:nsubj\t_
6\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t6\tpunct\t6:punct\t_

# sent_id = s33
# text = Along with changing numbers.
1\tAlong\talong\tADP\tIN\t_\t3\tmark\t3:mark\t_
2\twith\twith\tADP\tIN\t_\t1\tfixed\t1:fixed\t_
3\tchanging\tchange\tVERB\tVBG\tVerbForm=Ger\t0\troot\t0:root\t_
4\tnumbers\tnumber\tNOUN\tNNS\tNumber=Plur\t3\tobj\t3:obj\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s34
# text = It took quite a while.
1\tIt\tit\tPRON\tPRP\tCase=Nom|Gender=Neut|Number=Sing|Person=3|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\ttook\ttake\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tquite\tquite\tDET\tPDT\tPronType=Ind\t5\tdet:predet\t5:det:predet\t_
4\ta\ta\tDET\tDT\tDefinite=Ind|PronType=Art\t5\tdet\t5:det\t_
5\twhile\twhile\tNOUN\tNN\tNumber=Sing\t2\tobj\t2:obj\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s35
# text = Keep them lovely kebabs coming.
1\tKeep\tkeep\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\tthem\tthem\tDET\tDT\tNumber=Plur|PronType=Dem|Style=Vrnc\t4\tdet\t4:det\t_
3\tlovely\tlovely\tADJ\tJJ\tDegree=Pos\t4\tamod\t4:amod\t_
4\tkebabs\tkebab\tNOUN\tNNS\tNumber=Plur\t1\tobj\t1:obj|5:nsubj:xsubj\t_
5\tcoming\tcome\tVERB\tVBG\tVerbForm=Ger\t1\txcomp\t1:xcomp\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s36
# text = Wtf is this?
1\tWtf\twtf\tPRON\tWP\tPronType=Int|Style=Expr\t0\troot\t0:root\t_
2\tis\tbe\tAUX\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t1\tcop\t1:cop\t_
3\tthis\tthis\tPRON\tDT\tNumber=Sing|PronType=Dem\t1\tnsubj\t1:nsubj\tSpaceAfter=No
4\t?\t?\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s37
# text = Judges et al.
1\tJudges\tjudge\tNOUN\tNNS\tNumber=Plur\t0\troot\t0:root\t_
2\tet\tet\tX\tFW\t_\t3\tcc\t3:cc\tCorrectForm=et
3\tal\tal\tX\tFW\t_\t1\tconj\t1:conj:et\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s38
# text = Whatever age you are, start now.
1\tWhatever\twhatever\tDET\tWDT\tPronType=Int\t2\tdet\t2:det\t_
2\tage\tage\tNOUN\tNN\tNumber=Sing\t6\tadvcl\t6:advcl\t_
3\tyou\tyou\tPRON\tPRP\tCase=Nom|Person=2|PronType=Prs\t2\tnsubj\t2:nsubj\t_
4\tare\tbe\tAUX\tVBP\tMood=Ind|Number=Sing|Person=2|Tense=Pres|VerbForm=Fin\t2\tcop\t2:cop\t_
5\t,\t,\tPUNCT\t,\t_\t2\tpunct\t2:punct\t_
6\tstart\tstart\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
7\tnow\tnow\tADV\tRB\tPronType=Dem\t6\tadvmod\t6:advmod\tSpaceAfter=No
8\t.\t.\tPUNCT\t.\t_\t6\tpunct\t6:punct\t_

# sent_id = s39
# text = Whosoever will may come.
1\tWhosoever\twhosoever\tPRON\tWP\tPronType=Rel\t4\tnsubj\t4:nsubj\t_
2\twill\twill\tAUX\tMD\tVerbForm=Fin\t1\tacl:relcl\t1:acl:relcl\t_
3\tmay\tmay\tAUX\tMD\tVerbForm=Fin\t4\taux\t4:aux\t_
4\tcome\tcome\tVERB\tVB\tVerbForm=Inf\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s40
# text = Stuffing oneself through fireplaces.
1\tStuffing\tstuff\tVERB\tVBG\tVerbForm=Ger\t0\troot\t0:root\t_
2\toneself\toneself\tPRON\tPRP\tCase=Acc|Number=Sing|Person=3|PronType=Prs\t1\tobj\t1:obj\t_
3\tthrough\tthrough\tADP\tIN\t_\t4\tcase\t4:case\t_
4\tfireplaces\tfireplace\tNOUN\tNNS\tNumber=Plur\t1\tobl\t1:obl:through\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s41
# text = S/he left.
1\tS/he\ts/he\tPRON\tPRP\tCase=Nom|Gender=Fem,Masc|Number=Sing|Person=3|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s42
# text = Imagine yonder table.
1\tImagine\timagine\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\tyonder\tyonder\tDET\tDT\tPronType=Dem\t3\tdet\t3:det\t_
3\ttable\ttable\tNOUN\tNN\tNumber=Sing\t1\tobj\t1:obj\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s43
# text = Called Une Semaine.
1\tCalled\tcall\tVERB\tVBN\tTense=Past|VerbForm=Part\t0\troot\t0:root\t_
2\tUne\tune\tDET\tFW\tForeign=Yes|PronType=Ind\t3\tdet\t3:det\t_
3\tSemaine\tsemaine\tX\tFW\tForeign=Yes\t1\tobj\t1:obj\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s44
# text = We went over there.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\twent\tgo\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tover\tover\tADP\tIN\t_\t4\tcase\t4:case\t_
4\tthere\tthere\tPRON\tPRP\tCase=Acc|PronType=Dem\t2\tobl\t2:obl:over\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_
"""


class PipelineTest(unittest.TestCase):
    def run_retag(
        self,
        sample_conllu: str = SAMPLE_CONLLU,
        include_text: bool = False,
    ) -> tuple[Path, list[dict[str, str]]]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        input_path = tmp_path / "sample.conllu"
        output_path = tmp_path / "output.tsv"
        input_path.write_text(sample_conllu, encoding="utf-8")

        cmd = [
            sys.executable,
            str(RETAG_SCRIPT),
            str(input_path),
            "--rules",
            str(RULES_PATH),
            "--output",
            str(output_path),
        ]
        if include_text:
            cmd.append("--include-text")
        subprocess.run(cmd, check=True, cwd=REPO_ROOT)

        with output_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        return output_path, rows

    def test_default_output_omits_sentence_text_and_matches_rules(self) -> None:
        output_path, rows = self.run_retag(include_text=False)
        self.assertEqual(len(rows), 68)
        self.assertNotIn("sentence_text", rows[0])

        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "1")]["rule_id"], "determiner-demonstrative-headless")
        self.assertEqual(by_sent_token[("s1", "1")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s2", "3")]["rule_id"], "subordinator-relative-that")
        self.assertEqual(by_sent_token[("s2", "3")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s2", "3")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s3", "1")]["rule_id"], "determiner-wh-headless")
        self.assertEqual(by_sent_token[("s3", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s4", "1")]["rule_id"], "there-expletive")
        self.assertEqual(by_sent_token[("s5", "1")]["rule_id"], "preposition-sconj")
        self.assertEqual(by_sent_token[("s5", "1")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s6", "1")]["rule_id"], "determiner-whatever")
        self.assertEqual(by_sent_token[("s6", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s6", "1")]["br_subtype"], "whatever")
        self.assertEqual(by_sent_token[("s6", "1")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s7", "2")]["rule_id"], "preposition-intransitive-adv")
        self.assertEqual(by_sent_token[("s7", "2")]["br_subtype"], "intransitive")
        self.assertEqual(by_sent_token[("s8", "3")]["rule_id"], "verb-infinitival-to")
        self.assertEqual(by_sent_token[("s8", "3")]["br_cat"], "verb")
        self.assertEqual(by_sent_token[("s8", "3")]["br_subtype"], "auxiliary_infinitival")
        self.assertEqual(by_sent_token[("s9", "1")]["rule_id"], "subordinator-for-infinitival")
        self.assertEqual(by_sent_token[("s9", "1")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s9", "1")]["br_subtype"], "infinitival")
        self.assertEqual(by_sent_token[("s9", "3")]["rule_id"], "verb-infinitival-to")
        self.assertEqual(by_sent_token[("s10", "2")]["rule_id"], "preposition-sconj")
        self.assertEqual(by_sent_token[("s10", "2")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s11", "2")]["rule_id"], "coordinator-and")
        self.assertEqual(by_sent_token[("s11", "2")]["br_cat"], "coordinator")
        self.assertEqual(by_sent_token[("s11", "2")]["br_subtype"], "additive")
        self.assertEqual(by_sent_token[("s12", "2")]["rule_id"], "coordinator-as-well-as")
        self.assertEqual(by_sent_token[("s12", "2")]["br_cat"], "coordinator")
        self.assertEqual(by_sent_token[("s12", "2")]["br_subtype"], "additive")
        self.assertEqual(by_sent_token[("s12", "2")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s13", "2")]["rule_id"], "coordinator-slash")
        self.assertEqual(by_sent_token[("s13", "2")]["br_cat"], "coordinator")
        self.assertEqual(by_sent_token[("s13", "2")]["br_subtype"], "disjunctive")
        self.assertEqual(by_sent_token[("s14", "3")]["rule_id"], "negative-enclitic-nt")
        self.assertEqual(by_sent_token[("s14", "3")]["br_cat"], "morpheme")
        self.assertEqual(by_sent_token[("s15", "1")]["rule_id"], "numerative-cardinal-determiner")
        self.assertEqual(by_sent_token[("s15", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s15", "1")]["br_subtype"], "cardinal")
        self.assertEqual(by_sent_token[("s16", "1")]["rule_id"], "numerative-cardinal-factor")
        self.assertEqual(by_sent_token[("s16", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s16", "1")]["br_subtype"], "cardinal_factor")
        self.assertEqual(by_sent_token[("s16", "2")]["rule_id"], "numerative-cardinal-determiner")
        self.assertEqual(by_sent_token[("s17", "1")]["rule_id"], "numerative-cardinal-fused-head")
        self.assertEqual(by_sent_token[("s17", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s17", "1")]["br_subtype"], "cardinal_fused_head")
        self.assertEqual(by_sent_token[("s18", "2")]["rule_id"], "numerative-ordinal-adjective")
        self.assertEqual(by_sent_token[("s18", "2")]["br_cat"], "adjective")
        self.assertEqual(by_sent_token[("s18", "2")]["br_subtype"], "ordinal")
        self.assertEqual(by_sent_token[("s19", "2")]["rule_id"], "pronoun-one-negative")
        self.assertEqual(by_sent_token[("s19", "2")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s19", "2")]["br_subtype"], "negative")
        self.assertEqual(by_sent_token[("s20", "4")]["rule_id"], "pronoun-one-reciprocal")
        self.assertEqual(by_sent_token[("s20", "4")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s20", "4")]["br_subtype"], "reciprocal")
        self.assertEqual(by_sent_token[("s21", "2")]["rule_id"], "subordinator-sconj-that")
        self.assertEqual(by_sent_token[("s21", "2")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s21", "2")]["br_subtype"], "declarative")
        self.assertEqual(by_sent_token[("s22", "2")]["rule_id"], "subordinator-whether")
        self.assertEqual(by_sent_token[("s22", "2")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s22", "2")]["br_subtype"], "interrogative")
        self.assertEqual(by_sent_token[("s23", "1")]["rule_id"], "determiner-quantificational-marker-cconj")
        self.assertEqual(by_sent_token[("s23", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s23", "1")]["br_subtype"], "quantificational")
        self.assertEqual(by_sent_token[("s24", "3")]["rule_id"], "determiner-quantificational-marker-adv")
        self.assertEqual(by_sent_token[("s24", "3")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s24", "3")]["br_subtype"], "quantificational")
        self.assertEqual(by_sent_token[("s25", "2")]["rule_id"], "subordinator-if-complement")
        self.assertEqual(by_sent_token[("s25", "2")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s25", "2")]["br_subtype"], "interrogative")
        self.assertEqual(by_sent_token[("s26", "1")]["rule_id"], "preposition-sconj")
        self.assertEqual(by_sent_token[("s26", "1")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s26", "1")]["br_subtype"], "clausal")
        self.assertEqual(by_sent_token[("s27", "2")]["rule_id"], "preposition-along-with-case")
        self.assertEqual(by_sent_token[("s27", "2")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s27", "2")]["br_subtype"], "complex_with")
        self.assertEqual(by_sent_token[("s27", "2")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s28", "3")]["rule_id"], "preposition-sconj-so")
        self.assertEqual(by_sent_token[("s28", "3")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s28", "3")]["br_subtype"], "clausal")
        self.assertEqual(by_sent_token[("s29", "3")]["rule_id"], "subordinator-if-complement")
        self.assertEqual(by_sent_token[("s29", "7")]["rule_id"], "subordinator-if-complement-conj")
        self.assertEqual(by_sent_token[("s29", "7")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s29", "7")]["br_subtype"], "interrogative")
        self.assertEqual(by_sent_token[("s30", "4")]["rule_id"], "coordinator-yet")
        self.assertEqual(by_sent_token[("s30", "4")]["br_cat"], "coordinator")
        self.assertEqual(by_sent_token[("s30", "4")]["br_subtype"], "adversative")
        self.assertEqual(by_sent_token[("s30", "4")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s31", "4")]["rule_id"], "coordinator-rather-than-cc")
        self.assertEqual(by_sent_token[("s31", "4")]["br_cat"], "coordinator")
        self.assertEqual(by_sent_token[("s31", "4")]["br_subtype"], "rather_than")
        self.assertEqual(by_sent_token[("s31", "4")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s32", "1")]["rule_id"], "preposition-rather-than-mark")
        self.assertEqual(by_sent_token[("s32", "1")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s32", "1")]["br_subtype"], "clausal")
        self.assertEqual(by_sent_token[("s32", "1")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s33", "1")]["rule_id"], "preposition-along-with-mark")
        self.assertEqual(by_sent_token[("s33", "1")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s33", "1")]["br_subtype"], "clausal")
        self.assertEqual(by_sent_token[("s33", "1")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s34", "3")]["rule_id"], "adverb-quite")
        self.assertEqual(by_sent_token[("s34", "3")]["br_cat"], "adverb")
        self.assertEqual(by_sent_token[("s34", "3")]["br_subtype"], "degree")
        self.assertEqual(by_sent_token[("s34", "3")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s35", "2")]["rule_id"], "determiner-dialectal-them")
        self.assertEqual(by_sent_token[("s35", "2")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s35", "2")]["br_subtype"], "demonstrative")
        self.assertEqual(by_sent_token[("s35", "2")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s36", "1")]["rule_id"], "determiner-expressive-wtf")
        self.assertEqual(by_sent_token[("s36", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s36", "1")]["br_subtype"], "fused_head")
        self.assertEqual(by_sent_token[("s36", "1")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s37", "2")]["rule_id"], "coordinator-et-al")
        self.assertEqual(by_sent_token[("s37", "2")]["br_cat"], "coordinator")
        self.assertEqual(by_sent_token[("s37", "2")]["br_subtype"], "additive")
        self.assertEqual(by_sent_token[("s37", "2")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s38", "1")]["rule_id"], "determiner-whatever")
        self.assertEqual(by_sent_token[("s38", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s38", "1")]["br_subtype"], "whatever")
        self.assertEqual(by_sent_token[("s38", "1")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s39", "1")]["rule_id"], "pronoun-wh")
        self.assertEqual(by_sent_token[("s39", "1")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s39", "1")]["br_subtype"], "wh")
        self.assertEqual(by_sent_token[("s39", "1")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s40", "2")]["rule_id"], "pronoun-reflexive")
        self.assertEqual(by_sent_token[("s40", "2")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s40", "2")]["br_subtype"], "reflexive")
        self.assertEqual(by_sent_token[("s40", "2")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s41", "1")]["rule_id"], "pronoun-personal")
        self.assertEqual(by_sent_token[("s41", "1")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s41", "1")]["br_subtype"], "personal")
        self.assertEqual(by_sent_token[("s41", "1")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s42", "2")]["rule_id"], "determiner-demonstrative-yonder")
        self.assertEqual(by_sent_token[("s42", "2")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s42", "2")]["br_subtype"], "demonstrative")
        self.assertEqual(by_sent_token[("s42", "2")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s43", "2")]["rule_id"], "determiner-foreign-une")
        self.assertEqual(by_sent_token[("s43", "2")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s43", "2")]["br_subtype"], "article")
        self.assertEqual(by_sent_token[("s43", "2")]["needs_review"], "false")
        self.assertEqual(by_sent_token[("s44", "4")]["rule_id"], "preposition-there-locative")
        self.assertEqual(by_sent_token[("s44", "4")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s44", "4")]["br_subtype"], "intransitive")
        self.assertEqual(by_sent_token[("s44", "4")]["needs_review"], "false")

        with output_path.open(encoding="utf-8") as handle:
            header = handle.readline().rstrip("\n").split("\t")
        self.assertNotIn("sentence_text", header)

    def test_include_text_adds_sentence_text_column(self) -> None:
        output_path, rows = self.run_retag(include_text=True)
        self.assertEqual(rows[0]["sentence_text"], "This helps.")
        with output_path.open(encoding="utf-8") as handle:
            header = handle.readline().rstrip("\n").split("\t")
        self.assertIn("sentence_text", header)

    def test_there_reparandum_is_preposition(self) -> None:
        sample = """# sent_id = s1
# text = There - you can see it.
1\tThere\tthere\tPRON\tEX\tPronType=Dem\t5\treparandum\t5:reparandum\t_
2\t-\t-\tPUNCT\t:\t_\t1\tpunct\t1:punct\t_
3\tyou\tyou\tPRON\tPRP\tCase=Nom|Number=Sing|Person=2|PronType=Prs\t5\tnsubj\t5:nsubj\t_
4\tcan\tcan\tAUX\tMD\tVerbForm=Fin\t5\taux\t5:aux\t_
5\tsee\tsee\tVERB\tVB\tVerbForm=Inf\t0\troot\t0:root\t_
6\tit\tit\tPRON\tPRP\tCase=Acc|Gender=Neut|Number=Sing|Person=3|PronType=Prs\t5\tobj\t5:obj\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t5\tpunct\t5:punct\t_
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "1")]["rule_id"], "preposition-there-locative")
        self.assertEqual(by_sent_token[("s1", "1")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s1", "1")]["br_subtype"], "intransitive")
        self.assertEqual(by_sent_token[("s1", "1")]["needs_review"], "false")

    def test_self_compound_initial_is_nounal(self) -> None:
        sample = """# sent_id = s1
# text = Don't be too self-deprecating.
1-2\tDon't\t_\t_\t_\t_\t_\t_\t_\t_
1\tDo\tdo\tAUX\tVB\tVerbForm=Inf\t7\taux\t7:aux\t_
2\tn't\tnot\tPART\tRB\tPolarity=Neg\t7\tadvmod\t7:advmod\t_
3\tbe\tbe\tAUX\tVB\tMood=Imp|Person=2|VerbForm=Fin\t7\tcop\t7:cop\t_
4\ttoo\ttoo\tADV\tRB\tDegree=Pos\t7\tadvmod\t7:advmod\t_
5\tself\tself\tPRON\tPRP\tCase=Acc|Number=Sing|Person=3|PronType=Prs\t7\tcompound\t7:compound\tSpaceAfter=No
6\t-\t-\tPUNCT\tHYPH\t_\t5\tpunct\t5:punct\tSpaceAfter=No
7\tdeprecating\tdeprecating\tADJ\tJJ\tDegree=Pos\t0\troot\t0:root\tSpaceAfter=No
8\t.\t.\tPUNCT\t.\t_\t7\tpunct\t7:punct\t_
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "5")]["rule_id"], "noun-self-compound-initial")
        self.assertEqual(by_sent_token[("s1", "5")]["br_cat"], "noun")
        self.assertEqual(by_sent_token[("s1", "5")]["br_subtype"], "self_compound_initial")
        self.assertEqual(by_sent_token[("s1", "5")]["needs_review"], "false")

    def test_mat_foreign_component_is_not_determinative(self) -> None:
        sample = """# sent_id = s1
# text = To be 'Mat Fereder'.
1\tTo\tto\tPART\tTO\t_\t4\tmark\t4:mark\t_
2\tbe\tbe\tAUX\tVB\tVerbForm=Inf\t4\tcop\t4:cop\t_
3\t'\t'\tPUNCT\t``\t_\t4\tpunct\t4:punct\tSpaceAfter=No
4\tMat\tMat\tDET\tFW\tPronType=Ind\t5\tdet\t5:det\t_
5\tFereder\tFereder\tX\tFW\t_\t0\troot\t0:root\tSpaceAfter=No
6\t'\t'\tPUNCT\t''\t_\t5\tpunct\t5:punct\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t5\tpunct\t5:punct\t_
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "4")]["rule_id"], "foreign-name-mat")
        self.assertEqual(by_sent_token[("s1", "4")]["br_cat"], "x")
        self.assertEqual(by_sent_token[("s1", "4")]["br_subtype"], "foreign_component")
        self.assertEqual(by_sent_token[("s1", "4")]["needs_review"], "false")

    def test_delexicalized_structural_rules_cover_pronouns_and_determiners(self) -> None:
        sample = """# sent_id = s1
# text = _ _ _
1\t_\t_\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\tLem=*LOWER*|Len=3
2\t_\t_\tNOUN\tNN\tNumber=Sing\t0\troot\t0:root\tLem=_|Len=5
3\t_\t_\tPRON\tPRP\tCase=Nom|Number=Sing|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\tLem=_|Len=1
4\t_\t_\tPRON\tPRP$\tCase=Gen|Number=Sing|Person=1|Poss=Yes|PronType=Prs\t2\tnmod:poss\t2:nmod:poss\tLem=_|Len=2
5\t_\t_\tPRON\tEX\tPronType=Dem\t6\texpl\t6:expl\tLem=*LOWER*|Len=5
6\t_\t_\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t2\tacl:relcl\t2:acl:relcl\tLem=be|Len=2
7\t_\t_\tPRON\tDT\tNumber=Sing|PronType=Dem\t2\tobj\t2:obj\tLem=*LOWER*|Len=4|SpaceAfter=No
8\t_\t_\tPRON\tNN\tPronType=Ind\t2\tobj\t2:obj\tLem=_|Len=8|SpaceAfter=No
9\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\tLem=_|Len=1
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "1")]["rule_id"], "determiner-articles-structural")
        self.assertEqual(by_sent_token[("s1", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s1", "3")]["rule_id"], "pronoun-personal-structural")
        self.assertEqual(by_sent_token[("s1", "3")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s1", "4")]["rule_id"], "pronoun-possessive-structural")
        self.assertEqual(by_sent_token[("s1", "4")]["br_subtype"], "possessive")
        self.assertEqual(by_sent_token[("s1", "5")]["rule_id"], "pronoun-expletive-structural")
        self.assertEqual(by_sent_token[("s1", "5")]["br_subtype"], "expletive")
        self.assertEqual(by_sent_token[("s1", "7")]["rule_id"], "determiner-demonstrative-headless-structural")
        self.assertEqual(by_sent_token[("s1", "7")]["br_subtype"], "demonstrative_head")
        self.assertEqual(by_sent_token[("s1", "8")]["rule_id"], "determiner-indefinite-structural")
        self.assertEqual(by_sent_token[("s1", "8")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s1", "8")]["br_subtype"], "indefinite")

    def test_delexicalized_misc_hints_cover_relative_wh_and_corrected_forms(self) -> None:
        sample = """# sent_id = s1
# text = _ _ _ _ .
1\t_\t_\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\tLem=_|Len=4
2\t_\t_\tPRON\tWP\tPronType=Rel\t3\tnsubj\t1:ref\tLem=_|Len=3
3\t_\t_\tVERB\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t1\tacl:relcl\t1:acl:relcl\tLem=_|Len=4
4\t_\t_\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tLem=_|Len=5|SpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s2
# text = _ _ _ _ .
1\t_\t_\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\tLem=_|Len=5
2\t_\t_\tPRON\tWDT\tPronType=Rel\t3\tnsubj\t1:ref\tLem=_|Len=4
3\t_\t_\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t1\tacl:relcl\t1:acl:relcl\tLem=_|Len=5
4\t_\t_\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tLem=_|Len=5|SpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s3
# text = _ _ _ _ .
1\t_\t_\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\tLem=_|Len=6
2\t_\t_\tPRON\tWDT\tPronType=Rel\t3\tobj\t1:ref\tLem=_|Len=5
3\t_\t_\tVERB\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t1\tacl:relcl\t1:acl:relcl\tLem=_|Len=6
4\t_\t_\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tLem=_|Len=5|SpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s4
# text = _ _ _ _ .
1\t_\t_\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\tLem=_|Len=4
2\t_\t_\tPRON\tWDT\tPronType=Rel|Typo=Yes\t3\tobj\t1:ref\tCorrectForm=that|Lem=that|Len=4|XML=<sic ana:::\"that\"></sic>
3\t_\t_\tVERB\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t1\tacl:relcl\t1:acl:relcl\tLem=_|Len=4
4\t_\t_\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tLem=_|Len=5|SpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s5
# text = _ _ _ _ .
1\t_\t_\tVERB\tVB\tVerbForm=Inf\t0\troot\t0:root\tLem=_|Len=4
2\t_\t_\tPRON\tWP\tPronType=Rel\t1\tobj\t1:obj\tLem=_|Len=8|MSeg=what-ever
3\t_\t_\tAUX\tMD\tVerbForm=Fin\t1\taux\t1:aux\tLem=_|Len=4
4\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s6
# text = _ _ _ _ .
1\t_\t_\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\tLem=_|Len=4
2\t_\t_\tPRON\tWP$\tPronType=Rel|Typo=Yes\t3\tnmod:poss\t1:ref|3:nmod:poss\tCorrectForm=whose|Lem=whose|Len=5|MSeg=who-'s
3\t_\t_\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\tLem=_|Len=5
4\t_\t_\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tLem=_|Len=5|SpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "2")]["rule_id"], "pronoun-wh-relative-ref-structural")
        self.assertEqual(by_sent_token[("s1", "2")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s1", "2")]["br_subtype"], "wh")
        self.assertEqual(by_sent_token[("s2", "2")]["rule_id"], "subordinator-relative-that-structural")
        self.assertEqual(by_sent_token[("s2", "2")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s2", "2")]["br_subtype"], "relative")
        self.assertEqual(by_sent_token[("s3", "2")]["rule_id"], "determiner-wh-headless-relative-structural")
        self.assertEqual(by_sent_token[("s3", "2")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s3", "2")]["br_subtype"], "fused_head")
        self.assertEqual(by_sent_token[("s4", "2")]["rule_id"], "subordinator-relative-that")
        self.assertEqual(by_sent_token[("s4", "2")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s4", "2")]["br_subtype"], "relative")
        self.assertEqual(by_sent_token[("s5", "2")]["rule_id"], "determiner-whatever-mseg")
        self.assertEqual(by_sent_token[("s5", "2")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s5", "2")]["br_subtype"], "whatever")
        self.assertEqual(by_sent_token[("s6", "2")]["rule_id"], "pronoun-possessive")
        self.assertEqual(by_sent_token[("s6", "2")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s6", "2")]["br_subtype"], "possessive")

    def test_lexical_gap_fill_rules_cover_bare_one_relative_that_and_where(self) -> None:
        sample = """# sent_id = s1
# text = One expects gains.
1\tOne\tone\tPRON\tPRP\t_\t2\tnsubj\t2:nsubj\t_
2\texpects\texpect\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\t_
3\tgains\tgain\tNOUN\tNNS\tNumber=Plur\t2\tobj\t2:obj\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s2
# text = the thing that happened.
1\tthe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\tthing\tthing\tNOUN\tNN\tNumber=Sing\t0\troot\t0:root\t_
3\tthat\tthat\tPRON\tIN\t_\t4\tobj\t2:ref\t_
4\thappened\thappen\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t2\tacl:relcl\t2:acl:relcl\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s3
# text = We went to where.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\twent\tgo\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tto\tto\tADP\tIN\t_\t4\tcase\t4:case\t_
4\twhere\twhere\tPRON\tWRB\tPronType=Int\t2\tobl\t2:obl:to\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s4
# text = the means whereby she won.
1\tthe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\tmeans\tmean\tNOUN\tNNS\tNumber=Plur\t0\troot\t0:root\t_
3\twhereby\twhereby\tPRON\tWRB\tPronType=Rel\t5\tobl\t5:obl\t_
4\tshe\tshe\tPRON\tPRP\tCase=Nom|Number=Sing|Person=3|PronType=Prs\t5\tnsubj\t5:nsubj\t_
5\twon\twin\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t2\tacl:relcl\t2:acl:relcl\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "1")]["rule_id"], "pronoun-generic-one-bare")
        self.assertEqual(by_sent_token[("s1", "1")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s1", "1")]["br_subtype"], "generic")
        self.assertEqual(by_sent_token[("s2", "3")]["rule_id"], "subordinator-relative-that-ref")
        self.assertEqual(by_sent_token[("s2", "3")]["br_cat"], "subordinator")
        self.assertEqual(by_sent_token[("s2", "3")]["br_subtype"], "relative")
        self.assertEqual(by_sent_token[("s3", "4")]["rule_id"], "preposition-where-pron")
        self.assertEqual(by_sent_token[("s3", "4")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s3", "4")]["br_subtype"], "intransitive")
        self.assertEqual(by_sent_token[("s4", "3")]["rule_id"], "preposition-whereby")
        self.assertEqual(by_sent_token[("s4", "3")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s4", "3")]["br_subtype"], "intransitive")

    def test_lines_residue_rules_cover_foreign_strings_articles_and_misc_lexical_items(self) -> None:
        sample = """# sent_id = s1
# text = A great many have.
1\tA\ta\tPRON\tDT\tCase=Nom\t4\tnsubj\t4:nsubj\t_
2\tgreat\tgreat\tADJ\tJJ\tDegree=Pos\t1\tfixed\t1:fixed\t_
3\tmany\tmany\tADJ\tJJ\tDegree=Pos\t1\tfixed\t1:fixed\t_
4\thave\thave\tVERB\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s2
# text = Morituri te salutant.
1\tMorituri\tmorituri\tNOUN\tNN\tForeign=Yes\t3\tnsubj\t3:nsubj\t_
2\tte\tte\tPRON\t_\tForeign=Yes\t3\tobj\t3:obj\t_
3\tsalutant\tsalutant\tVERB\tVB\tForeign=Yes\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s3
# text = Du calme.
1\tDu\tdu\tDET\tFGN\t_\t2\tdet\t2:det\t_
2\tcalme\tcalme\tNOUN\tNN\t_\t0\troot\t0:root\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s4
# text = One day passed.
1\tOne\tone\tDET\tIND-SG\t_\t2\tdet\t2:det\t_
2\tday\tday\tNOUN\tNN\tNumber=Sing\t3\tnsubj\t3:nsubj\t_
3\tpassed\tpass\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s5
# text = One found oneself there.
1\tOne\tone\tPRON\tNN\t_\t2\tnsubj\t2:nsubj\t_
2\tfound\tfind\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\toneself\tone\tPRON\tPRP\tReflex=Yes\t2\tobj\t2:obj\t_
4\tthere\tthere\tADV\tRB\t_\t2\tadvmod\t2:advmod\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s6
# text = Others arrived.
1\tOthers\tother\tPRON\tJJ\tCase=Nom\t2\tnsubj\t2:nsubj\t_
2\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s7
# text = It has a department of its own.
1\tIt\tit\tPRON\tPRP\tCase=Nom|Number=Sing|Person=3|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\thas\thave\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\t_
3\ta\ta\tDET\tDT\tDefinite=Ind|PronType=Art\t4\tdet\t4:det\t_
4\tdepartment\tdepartment\tNOUN\tNN\tNumber=Sing\t2\tobj\t2:obj\t_
5\tof\tof\tADP\tIN\t_\t7\tcase\t7:case\t_
6\tits\tits\tPRON\tPRP$\tCase=Gen|Gender=Neut|Number=Sing|Person=3|Poss=Yes|PronType=Prs\t7\tnmod:poss\t7:nmod:poss\t_
7\town\town\tPRON\tADJ\tCase=Nom\t4\tnmod\t4:nmod:of\tSpaceAfter=No
8\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s8
# text = wha' d' you say?
1\twha'\twhat\tPRON\tWH\t_\t4\tobj\t4:obj\t_
2\td'\tdo\tAUX\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t4\taux\t4:aux\t_
3\tyou\tyou\tPRON\tPRP\tCase=Nom|Person=2|PronType=Prs\t4\tnsubj\t4:nsubj\t_
4\tsay\tsay\tVERB\tVB\tVerbForm=Inf\t0\troot\t0:root\tSpaceAfter=No
5\t?\t?\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s9
# text = Much has been aired.
1\tMuch\tMuch\tPRON\tADJ\tCase=Nom\t4\tnsubj:pass\t4:nsubj:pass\t_
2\thas\thave\tAUX\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t4\taux\t4:aux\t_
3\tbeen\tbe\tAUX\tVBN\tTense=Past|VerbForm=Part\t4\taux:pass\t4:aux:pass\t_
4\taired\taire\tVERB\tVBN\tTense=Past|VerbForm=Part|Voice=Pass\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s10
# text = The big ones arrived.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t3\tdet\t3:det\t_
2\tbig\tbig\tADJ\tJJ\tDegree=Pos\t3\tamod\t3:amod\t_
3\tones\tone\tPRON\tNN\tCase=Nom\t4\tnsubj\t4:nsubj\t_
4\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s11
# text = The old one arrived.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t3\tdet\t3:det\t_
2\told\told\tADJ\tJJ\tDegree=Pos\t3\tamod\t3:amod\t_
3\tone\tone\tPRON\tNN\tCase=Nom\t4\tnsubj\t4:nsubj\t_
4\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "1")]["rule_id"], "determiner-articles-pron")
        self.assertEqual(by_sent_token[("s1", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s2", "2")]["rule_id"], "foreign-pronoun")
        self.assertEqual(by_sent_token[("s2", "2")]["br_cat"], "x")
        self.assertEqual(by_sent_token[("s3", "1")]["rule_id"], "foreign-determiner-fgn")
        self.assertEqual(by_sent_token[("s3", "1")]["br_cat"], "x")
        self.assertEqual(by_sent_token[("s4", "1")]["rule_id"], "numerative-cardinal-determiner-det")
        self.assertEqual(by_sent_token[("s4", "1")]["br_subtype"], "cardinal")
        self.assertEqual(by_sent_token[("s5", "3")]["rule_id"], "pronoun-reflexive-oneself-form")
        self.assertEqual(by_sent_token[("s5", "3")]["br_subtype"], "reflexive")
        self.assertEqual(by_sent_token[("s6", "1")]["rule_id"], "adjective-other")
        self.assertEqual(by_sent_token[("s6", "1")]["br_cat"], "adjective")
        self.assertEqual(by_sent_token[("s7", "7")]["rule_id"], "adjective-own")
        self.assertEqual(by_sent_token[("s7", "7")]["br_cat"], "adjective")
        self.assertEqual(by_sent_token[("s8", "1")]["rule_id"], "determiner-wh-headless-wha")
        self.assertEqual(by_sent_token[("s8", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s9", "1")]["rule_id"], "determiner-quantificational")
        self.assertEqual(by_sent_token[("s9", "1")]["br_subtype"], "quantificational")
        self.assertEqual(by_sent_token[("s10", "3")]["rule_id"], "noun-prop-word-ones")
        self.assertEqual(by_sent_token[("s10", "3")]["br_cat"], "noun")
        self.assertEqual(by_sent_token[("s10", "3")]["br_subtype"], "prop_word")
        self.assertEqual(by_sent_token[("s11", "3")]["rule_id"], "noun-prop-word-one-modified")
        self.assertEqual(by_sent_token[("s11", "3")]["br_cat"], "noun")
        self.assertEqual(by_sent_token[("s11", "3")]["br_subtype"], "prop_word")

    def test_additional_lexical_recovery_rules_cover_articles_possessives_demonstratives_relatives_and_partitives(self) -> None:
        sample = """# sent_id = s1
# text = An indicator helps.
1\tAn\t_\tDET\t_\t_\t2\tdet\t2:det\t_
2\tindicator\t_\tNOUN\t_\t_\t3\tnsubj\t3:nsubj\t_
3\thelps\t_\tVERB\t_\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s2
# text = Their ability matters.
1\tTheir\tthey\tDET\t_\t_\t2\tnmod\t2:nmod\t_
2\tability\t_\tNOUN\t_\t_\t3\tnsubj\t3:nsubj\t_
3\tmatters\t_\tVERB\t_\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s3
# text = This works.
1\tThis\t_\tPRON\t_\t_\t2\tnsubj\t2:nsubj\t_
2\tworks\t_\tVERB\t_\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s4
# text = We need that.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tneed\tneed\tVERB\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\t_
3\tthat\t_\tPRON\t_\t_\t2\tobj\t2:obj\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s5
# text = Those fields matter.
1\tThose\t_\tDET\t_\t_\t2\tdet\t2:det\t_
2\tfields\t_\tNOUN\t_\t_\t3\tnsubj\t3:nsubj\t_
3\tmatter\t_\tVERB\t_\tMood=Ind|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s6
# text = The flight that leaves.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\tflight\tflight\tNOUN\tNN\tNumber=Sing\t0\troot\t0:root\t_
3\tthat\tthat\tPRON\t_\tPronType=Rel\t4\tnsubj\t4:nsubj\t_
4\tleaves\tleave\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t2\tacl:relcl\t2:acl:relcl\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s7
# text = The device that works.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\tdevice\tdevice\tNOUN\tNN\tNumber=Sing\t0\troot\t0:root\t_
3\tthat\t_\tPRON\t_\t_\t4\tnsubj\t4:nsubj\t_
4\tworks\twork\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t2\tacl:relcl\t2:acl:relcl\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s8
# text = The date on which it occurs.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\tdate\tdate\tNOUN\tNN\tNumber=Sing\t0\troot\t0:root\t_
3\ton\ton\tADP\tIN\t_\t4\tcase\t4:case\t_
4\twhich\t_\tPRON\t_\t_\t6\tobl\t6:obl:on\t_
5\tit\tit\tPRON\tPRP\tCase=Nom|Number=Sing|Person=3|PronType=Prs\t6\tnsubj\t6:nsubj\t_
6\toccurs\toccur\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t2\tacl:relcl\t2:acl:relcl\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s9
# text = Require one of the items.
1\tRequire\trequire\tVERB\tVB\tVerbForm=Inf\t0\troot\t0:root\t_
2\tone\tone\tPRON\t_\t_\t1\tobj\t1:obj\t_
3\tof\tof\tADP\tIN\t_\t5\tcase\t5:case\t_
4\tthe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t5\tdet\t5:det\t_
5\titems\titem\tNOUN\tNNS\tNumber=Plur\t2\tnmod\t2:nmod\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s10
# text = The calls which he is authorised to terminate.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\tcalls\tcall\tNOUN\tNNS\tNumber=Plur\t0\troot\t0:root\t_
3\twhich\t_\tPRON\t_\t_\t8\tobj\t8:obj\t_
4\the\the\tPRON\tPRP\tCase=Nom|Number=Sing|Person=3|PronType=Prs\t6\tnsubj:pass\t6:nsubj:pass\t_
5\tis\tbe\tAUX\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t6\taux:pass\t6:aux:pass\t_
6\tauthorised\tauthorise\tVERB\tVBN\tTense=Past|VerbForm=Part\t2\tacl:relcl\t2:acl:relcl\t_
7\tto\tto\tPART\tTO\t_\t8\tmark\t8:mark\t_
8\tterminate\tterminate\tVERB\tVB\tVerbForm=Inf\t6\txcomp\t6:xcomp\tSpaceAfter=No
9\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s11
# text = The time from when it occurs.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\ttime\ttime\tNOUN\tNN\tNumber=Sing\t0\troot\t0:root\t_
3\tfrom\tfrom\tADP\tIN\t_\t4\tcase\t4:case\t_
4\twhen\t_\tPRON\t_\t_\t6\tobl\t6:obl:from\t_
5\tit\tit\tPRON\tPRP\tCase=Nom|Number=Sing|Person=3|PronType=Prs\t6\tnsubj\t6:nsubj\t_
6\toccurs\toccur\tVERB\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t2\tacl:relcl\t2:acl:relcl\tSpaceAfter=No
7\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s12
# text = Whichever is greater.
1\tWhichever\t_\tPRON\t_\t_\t3\tnsubj\t3:nsubj\t_
2\tis\tbe\tAUX\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t3\tcop\t3:cop\t_
3\tgreater\tgreat\tADJ\tJJR\tDegree=Cmp\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s13
# text = Other details matter.
1\tOther\tother\tDET\tDT\t_\t2\tdet\t2:det\t_
2\tdetails\tdetail\tNOUN\tNNS\tNumber=Plur\t3\tnsubj\t3:nsubj\t_
3\tmatter\tmatter\tVERB\tVBP\tMood=Ind|Tense=Pres|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s14
# text = The other arrived.
1\tThe\tthe\tDET\tDT\tDefinite=Def|PronType=Art\t2\tdet\t2:det\t_
2\tother\tother\tPRON\tJJ\t_\t3\tnsubj\t3:nsubj\t_
3\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s15
# text = Someone arrived.
1\tSomeone\tsomeone\tPRON\tNN\t_\t2\tnsubj\t2:nsubj\t_
2\tarrived\tarrive\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s16
# text = We saw half a loaf.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tsaw\tsee\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\thalf\thalf\tDET\tPDT\tNumForm=Word|NumType=Frac|PronType=Ind\t5\tcompound\t5:compound\t_
4\ta\ta\tDET\tDT\tDefinite=Ind|PronType=Art\t5\tdet\t5:det\t_
5\tloaf\tloaf\tNOUN\tNN\tNumber=Sing\t2\tobj\t2:obj\tSpaceAfter=No
6\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s17
# text = Such a plan failed.
1\tSuch\tsuch\tDET\tPDT\tPronType=Dem\t3\tdet:predet\t3:det:predet\t_
2\ta\ta\tDET\tDT\tDefinite=Ind|PronType=Art\t3\tdet\t3:det\t_
3\tplan\tplan\tNOUN\tNN\tNumber=Sing\t4\tnsubj\t4:nsubj\t_
4\tfailed\tfail\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t4\tpunct\t4:punct\t_

# sent_id = s18
# text = We headed over yonder.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\theaded\thead\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tover\tover\tADP\tIN\t_\t4\tcase\t4:case\t_
4\tyonder\tyonder\tADV\tRB\t_\t2\tobl\t2:obl:over\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        self.assertEqual(by_sent_token[("s1", "1")]["rule_id"], "determiner-articles")
        self.assertEqual(by_sent_token[("s2", "1")]["rule_id"], "pronoun-possessive-dependent-det")
        self.assertEqual(by_sent_token[("s2", "1")]["br_cat"], "pronoun")
        self.assertEqual(by_sent_token[("s2", "1")]["br_subtype"], "possessive")
        self.assertEqual(by_sent_token[("s3", "1")]["rule_id"], "determiner-demonstrative-headless")
        self.assertEqual(by_sent_token[("s4", "3")]["rule_id"], "determiner-demonstrative-headless")
        self.assertEqual(by_sent_token[("s4", "3")]["br_subtype"], "demonstrative_head")
        self.assertEqual(by_sent_token[("s5", "1")]["rule_id"], "determiner-demonstrative-headed")
        self.assertEqual(by_sent_token[("s6", "3")]["rule_id"], "subordinator-relative-that")
        self.assertEqual(by_sent_token[("s7", "3")]["rule_id"], "subordinator-relative-that-relcl")
        self.assertEqual(by_sent_token[("s8", "4")]["rule_id"], "determiner-wh-headless-relative-relcl")
        self.assertEqual(by_sent_token[("s9", "2")]["rule_id"], "numerative-cardinal-fused-head-one-of-pron")
        self.assertEqual(by_sent_token[("s9", "2")]["br_subtype"], "cardinal_fused_head")
        self.assertEqual(by_sent_token[("s10", "3")]["rule_id"], "determiner-wh-headless-relative-relcl")
        self.assertEqual(by_sent_token[("s11", "4")]["rule_id"], "preposition-when-pron")
        self.assertEqual(by_sent_token[("s11", "4")]["br_subtype"], "intransitive")
        self.assertEqual(by_sent_token[("s12", "1")]["rule_id"], "determiner-whichever")
        self.assertEqual(by_sent_token[("s13", "1")]["rule_id"], "adjective-other")
        self.assertEqual(by_sent_token[("s13", "1")]["br_cat"], "adjective")
        self.assertEqual(by_sent_token[("s14", "2")]["rule_id"], "adjective-other")
        self.assertEqual(by_sent_token[("s14", "2")]["br_cat"], "adjective")
        self.assertEqual(by_sent_token[("s15", "1")]["rule_id"], "determiner-indefinite")
        self.assertEqual(by_sent_token[("s15", "1")]["br_cat"], "determinative")
        self.assertEqual(by_sent_token[("s15", "1")]["br_subtype"], "indefinite")
        self.assertEqual(by_sent_token[("s16", "3")]["rule_id"], "numerative-half-noun")
        self.assertEqual(by_sent_token[("s16", "3")]["br_cat"], "noun")
        self.assertEqual(by_sent_token[("s16", "3")]["br_subtype"], "fractional")
        self.assertEqual(by_sent_token[("s17", "1")]["rule_id"], "adjective-such")
        self.assertEqual(by_sent_token[("s17", "1")]["br_cat"], "adjective")
        self.assertEqual(by_sent_token[("s17", "1")]["br_subtype"], "such")
        self.assertEqual(by_sent_token[("s18", "4")]["rule_id"], "preposition-yonder")
        self.assertEqual(by_sent_token[("s18", "4")]["br_cat"], "preposition")
        self.assertEqual(by_sent_token[("s18", "4")]["br_subtype"], "intransitive")

    def test_appendix_backed_intransitive_preposition_adv_expansion(self) -> None:
        sample = """# sent_id = s1
# text = We came in.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tcame\tcome\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tin\tin\tADV\tRB\t_\t2\tadvmod\t2:advmod\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s2
# text = It is over.
1\tIt\tit\tPRON\tPRP\tCase=Nom|Number=Sing|Person=3|PronType=Prs\t3\tnsubj\t3:nsubj\t_
2\tis\tbe\tAUX\tVBZ\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin\t3\tcop\t3:cop\t_
3\tover\tover\tADV\tRB\t_\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s3
# text = It happened years ago.
1\tIt\tit\tPRON\tPRP\tCase=Nom|Number=Sing|Person=3|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\thappened\thappen\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tyears\tyear\tNOUN\tNNS\tNumber=Plur\t2\tobl\t2:obl\t_
4\tago\tago\tADV\tRB\t_\t3\tadvmod\t3:advmod\tSpaceAfter=No
5\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s4
# text = We met before.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tmet\tmeet\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tbefore\tbefore\tADV\tRB\t_\t2\tadvmod\t2:advmod\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s5
# text = I visited once.
1\tI\tI\tPRON\tPRP\tCase=Nom|Number=Sing|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tvisited\tvisit\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tonce\tonce\tADV\tRB\t_\t2\tadvmod\t2:advmod\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s6
# text = They moved forward.
1\tThey\tthey\tPRON\tPRP\tCase=Nom|Number=Plur|Person=3|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\tmoved\tmove\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tforward\tforward\tADV\tRB\t_\t2\tadvmod\t2:advmod\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_

# sent_id = s7
# text = Keep ahead.
1\tKeep\tkeep\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\tahead\tahead\tADV\tRB\t_\t1\tadvmod\t1:advmod\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s8
# text = Move apart.
1\tMove\tmove\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\tapart\tapart\tADV\tRB\t_\t1\tadvmod\t1:advmod\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s9
# text = Hence we left.
1\tHence\thence\tADV\tRB\t_\t3\tadvmod\t3:advmod\t_
2\twe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t3\tnsubj\t3:nsubj\t_
3\tleft\tleave\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t3\tpunct\t3:punct\t_

# sent_id = s10
# text = Go forth.
1\tGo\tgo\tVERB\tVB\tMood=Imp|VerbForm=Fin\t0\troot\t0:root\t_
2\tforth\tforth\tADV\tRB\t_\t1\tadvmod\t1:advmod\tSpaceAfter=No
3\t.\t.\tPUNCT\t.\t_\t1\tpunct\t1:punct\t_

# sent_id = s11
# text = We walked out.
1\tWe\twe\tPRON\tPRP\tCase=Nom|Number=Plur|Person=1|PronType=Prs\t2\tnsubj\t2:nsubj\t_
2\twalked\twalk\tVERB\tVBD\tMood=Ind|Tense=Past|VerbForm=Fin\t0\troot\t0:root\t_
3\tout\tout\tADV\tRB\t_\t2\tadvmod\t2:advmod\tSpaceAfter=No
4\t.\t.\tPUNCT\t.\t_\t2\tpunct\t2:punct\t_
"""
        _, rows = self.run_retag(sample)
        by_sent_token = {(row["sent_id"], row["token_id"]): row for row in rows}
        for sent_id, token_id in [
            ("s1", "3"),
            ("s2", "3"),
            ("s3", "4"),
            ("s4", "3"),
            ("s5", "3"),
            ("s6", "3"),
            ("s7", "2"),
            ("s8", "2"),
            ("s9", "1"),
            ("s10", "2"),
            ("s11", "3"),
        ]:
            self.assertEqual(by_sent_token[(sent_id, token_id)]["rule_id"], "preposition-intransitive-adv")
            self.assertEqual(by_sent_token[(sent_id, token_id)]["br_cat"], "preposition")
            self.assertEqual(by_sent_token[(sent_id, token_id)]["br_subtype"], "intransitive")

    def test_audit_reports_expected_review_count(self) -> None:
        output_path, _ = self.run_retag(include_text=False)
        audit_path = output_path.parent / "audit.txt"
        cmd = [
            sys.executable,
            str(AUDIT_SCRIPT),
            str(output_path),
            "--output",
            str(audit_path),
        ]
        completed = subprocess.run(cmd, check=True, cwd=REPO_ROOT, capture_output=True, text=True)
        report = completed.stdout
        self.assertIn("Rows: 68", report)
        self.assertIn("Review rows: 0", report)
        self.assertIn("coordinator-as-well-as", report)
        self.assertIn("coordinator-yet", report)
        self.assertIn("coordinator-rather-than-cc", report)
        self.assertIn("preposition-along-with-case", report)
        self.assertIn("preposition-along-with-mark", report)
        self.assertIn("preposition-rather-than-mark", report)
        self.assertIn("preposition-there-locative", report)
        self.assertIn("determiner-whatever", report)
        self.assertIn("determiner-demonstrative-yonder", report)
        self.assertIn("determiner-foreign-une", report)
        self.assertIn("adverb-quite", report)
        self.assertIn("determiner-dialectal-them", report)
        self.assertIn("determiner-expressive-wtf", report)
        self.assertIn("coordinator-et-al", report)
        self.assertTrue(audit_path.exists())


if __name__ == "__main__":
    unittest.main()
