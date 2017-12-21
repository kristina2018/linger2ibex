#!/usr/bin/env python3
import sys
from itertools import chain
from functools import partial
from collections import namedtuple

SPACE_JOINER = ", "
LINGER_SPEC_PREFIX = "# "

IBEX_TEMPLATE = """var shuffleSequence = seq("intro", sepWith("sep", seq("practice", rshuffle({conditions}))))
var practiceItemTypes = ["practice"];

var defaults = [
    "Separator", {{
        transfer: 1000,
        normalMessage: "Please wait for the next sentence.",
        errorMessage: "Wrong. Please wait for the next sentence."
    }},
    "DashedSentence", {{
        mode: "self-paced reading"
    }},
    "AcceptabilityJudgment", {{
        as: ["1", "2", "3", "4", "5", "6", "7"],
        presentAsScale: true,
        instructions: "Use number keys or click boxes to answer.",
        leftComment: "(Bad)", rightComment: "(Good)"
    }},
    "Question", {{
        hasCorrect: true
    }},
    "Message", {{
        hideProgressBar: true
    }},
    "Form", {{
        hideProgressBar: true,
        continueOnReturn: true,
        saveReactionTime: true
    }}
];

var items = [
  ["sep", "Separator", {{ }}],
  ["setcounter", "__SetCounter__", {{ }}],
  ["intro", "Form", {{
    html: {{ include: "example_intro.html" }},
    validators: {{
      age: function (s) {{ if (s.match(/^\d+$/)) return true; 
                           else return "Bad value for \u2018age\u2019"; }}
      }}
  }} ],
    ["practice", "DashedSentence", 
     {{s: "This is a practice sentence to get you used to reading sentences like this."}}],
    ["practice", "DashedSentence", 
     {{s: "This is another practice sentence with a practice question following it."}},
                 "Question", {{hasCorrect: false, randomOrder: false,
                              q: "How would you like to answer this question?",
                              as: ["Press 1 or click here for this answer.",
                                   "Press 2 or click here for this answer.",
                                   "Press 3 or click here for this answer."]}}],
    ["practice", "DashedSentence", 
     {{s: "This is the last practice sentence before the experiment begins."}}],

    {stims}
];
"""

SPEC_TEMPLATE = """["{condition}", {item}]"""

STIM_TEMPLATE = """
[{spec}, "{stimtype}", {{s: "{sentence}"}}, {questions}]
""" 

QUESTION_TEMPLATE = """
"Question", {{q: "{question}", as: [{answers}]}}
"""

Stim = namedtuple("Stim", ['spec', 'sentence', 'questions'])
Spec = namedtuple("Spec", ['experiment', 'condition', 'item', 'rest'])
Question = namedtuple("Question", ['question', 'answers'])

def enquote(x):
    return "\"%s\"" % x

def consume(xs):
    for _ in xs:
        pass

def isplit(xs, sep):
    xs_it = iter(xs)
    while True:
        subit = iter(partial(next, xs_it), sep)
        try:
            probe = next(subit)
        except StopIteration:
            raise StopIteration
        yield chain([probe], subit)
        consume(subit)

flat = chain.from_iterable

def write_answers(answers):
    return SPACE_JOINER.join(map(enquote, answers))

def write_question(question):
    return QUESTION_TEMPLATE.format(
        question=question.question,
        answers=write_answers(question.answers)
    )

def write_questions(questions):
    return SPACE_JOINER.join(map(write_question, questions))

def write_conditions(spec):
    return "_".join([spec.experiment, spec.condition])

def write_spec(spec):
    # special case for fillers, which have no meaningful item number
    if spec.experiment.startswith("filler"):
        return enquote(write_conditions(spec)) 
    else:
        return SPEC_TEMPLATE.format(
            condition=write_conditions(spec),
            item=spec.item
        )

def write_stim(stimtype, stim):
    return STIM_TEMPLATE.format(
        spec=write_spec(stim.spec),
        stimtype=stimtype,
        sentence=stim.sentence,
        questions=write_questions(stim.questions)
    )
        
def parse_question(line):
    assert line.startswith("? ")
    line = line.strip("? ")
    question, answer = line.rsplit(" ", 1)
    if answer.lower() == "y" or answer.lower() == "yes":
        answers = ['Yes', 'No']
    elif answer.lower() == "n" or answer.lower() == "no":
        answers = ['No', 'Yes']
    else:
        raise ValueError("Unknown answer in question: %s" % line)
    return Question(question, answers)

def parse_stim(lines):
    spec_str, sentence, *questions = lines
    spec = parse_spec(spec_str)
    return Stim(spec, sentence, map(parse_question, questions))

def split_item(lines):
    lines = iter(lines)
    first_line = next(lines)
    assert first_line.startswith(LINGER_SPEC_PREFIX)
    stim = [first_line]
    for line in lines:
        if line.startswith(LINGER_SPEC_PREFIX):
            yield stim
            stim = []
        stim.append(line)
    yield stim

def parse_spec(line):
    assert line.startswith(LINGER_SPEC_PREFIX)
    line = line.strip(LINGER_SPEC_PREFIX)
    experiment, item, conditions, *rest = line.split()
    return Spec(experiment, conditions, int(item), rest)

def parse_linger(lines):
    lines = map(str.strip, lines)
    items = isplit(lines, "")
    stims = flat(map(split_item, items))
    return map(parse_stim, stims)

def write_ibex(stimtype, stims):
    stims = list(stims)
    write = partial(write_stim, stimtype)
    stims_string = ",".join(map(write, stims))
    conditions = {write_conditions(stim.spec) for stim in stims}
    conditions_str = ", ".join(map(enquote, conditions))
    return IBEX_TEMPLATE.format(
        conditions=conditions_str,
        stims=stims_string
    )

def run(stimtype, lines):
    stims = parse_linger(lines)
    return write_ibex(stimtype, stims)

def main(filename, stimtype="DashedSentence"):
    with open(filename) as infile:
        print(run(stimtype, infile))

if __name__ == '__main__':
    main(*sys.argv[1:])

        
