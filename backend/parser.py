from collections import defaultdict

def parse_grammar(input_strings):
    productions = []
    for s in input_strings:
        lhs, rhs_str = s.split(" -> ")
        rhs = rhs_str.split()
        productions.append((lhs, rhs))
    return productions

def augment_grammar(productions):
    start_symbol = productions[0][0]
    augmented = [("S'", [start_symbol])] + productions
    return augmented

def get_symbols(productions):
    non_terminals = set(lhs for lhs, rhs in productions)
    all_symbols = set(symbol for lhs, rhs in productions for symbol in rhs)
    terminals = all_symbols - non_terminals
    terminals.add("$")
    return non_terminals, terminals

def compute_nullable(productions, non_terminals):
    nullable = {nt: False for nt in non_terminals}
    changed = True
    while changed:
        changed = False
        for lhs, rhs in productions:
            if not rhs or all(symbol in non_terminals and nullable[symbol] for symbol in rhs):
                if not nullable[lhs]:
                    nullable[lhs] = True
                    changed = True
    return nullable

def compute_first(productions, non_terminals, terminals, nullable):
    first = {symbol: set() for symbol in non_terminals.union(terminals)}
    for t in terminals:
        first[t].add(t)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in productions:
            for symbol in rhs:
                first[lhs].update(first[symbol] - {""})
                if symbol not in nullable:
                    break
            if all(s in nullable for s in rhs):
                first[lhs].add("")
    return first

def closure(items, productions, first, nullable, terminals, non_terminals):
    I = set(items)
    changed = True
    while changed:
        changed = False
        new_items = set()
        for prod_index, dot_position, lookahead in I:
            prod = productions[prod_index]
            rhs = prod[1]
            if dot_position < len(rhs):
                symbol = rhs[dot_position]
                if symbol in non_terminals:
                    for b_prod_index, (b_lhs, b_rhs) in enumerate(productions):
                        if b_lhs == symbol:
                            beta = rhs[dot_position + 1:]
                            b_set = first_of_sequence(beta, lookahead, first, nullable, terminals, non_terminals)
                            for b in b_set:
                                new_item = (b_prod_index, 0, b)
                                if new_item not in I:
                                    new_items.add(new_item)
                                    changed = True
        I.update(new_items)
    return I

def first_of_sequence(sequence, lookahead, first, nullable, terminals, non_terminals):
    result = set()
    for symbol in sequence:
        result.update(first[symbol] - {""})
        if symbol not in nullable:
            return result
    result.add(lookahead)
    return result

def goto(items, symbol, productions, first, nullable, terminals, non_terminals):
    J = set()
    for prod_index, dot_position, lookahead in items:
        prod = productions[prod_index]
        rhs = prod[1]
        if dot_position < len(rhs) and rhs[dot_position] == symbol:
            new_item = (prod_index, dot_position + 1, lookahead)
            J.add(new_item)
    return closure(J, productions, first, nullable, terminals, non_terminals)

def build_dfa(productions, first, nullable, terminals, non_terminals):
    initial_item = (0, 0, "$")
    I0 = closure({initial_item}, productions, first, nullable, terminals, non_terminals)
    states = [I0]
    state_dict = {frozenset(I0): 0}
    transitions = {}
    to_process = [0]
    
    while to_process:
        current = to_process.pop(0)
        current_state = states[current]
        for symbol in terminals.union(non_terminals):
            next_state = goto(current_state, symbol, productions, first, nullable, terminals, non_terminals)
            if next_state:
                fs = frozenset(next_state)
                if fs not in state_dict:
                    state_index = len(states)
                    states.append(next_state)
                    state_dict[fs] = state_index
                    to_process.append(state_index)
                else:
                    state_index = state_dict[fs]
                transitions[(current, symbol)] = state_index
    return states, transitions

def build_parsing_table(states, transitions, productions, terminals, non_terminals):
    action = {}
    goto = {}
    
    for i, state in enumerate(states):
        for t in terminals:
            if (i, t) in transitions:
                action[(i, t)] = ("shift", transitions[(i, t)])
        
        for prod_index, dot_position, lookahead in state:
            prod = productions[prod_index]
            rhs = prod[1]
            if dot_position == len(rhs):
                if prod_index == 0:
                    action[(i, "$")] = ("accept", None)
                else:
                    action[(i, lookahead)] = ("reduce", prod_index)
        
        for nt in non_terminals:
            if (i, nt) in transitions:
                goto[(i, nt)] = transitions[(i, nt)]
    
    return action, goto

def compute_clr_parser(input_grammar):
    productions = parse_grammar(input_grammar)
    productions = augment_grammar(productions)
    non_terminals, terminals = get_symbols(productions)
    nullable = compute_nullable(productions, non_terminals)
    first = compute_first(productions, non_terminals, terminals, nullable)
    states, transitions = build_dfa(productions, first, nullable, terminals, non_terminals)
    action, goto = build_parsing_table(states, transitions, productions, terminals, non_terminals)
    return action, goto, productions, states

def parse_input(action, goto, productions, input_string):
    input_tokens = input_string.split() + ["$"]
    stack = [0]
    steps = []
    index = 0
    
    while True:
        state = stack[-1]
        token = input_tokens[index]
        step = {"Step": len(steps) + 1, "Stack": " ".join(map(str, stack)), "Input": " ".join(input_tokens[index:])}
        
        if (state, token) not in action:
            step["Action"] = "Error: No action for state {0} and token {1}".format(state, token)
            steps.append(step)
            break
        
        action_type, value = action[(state, token)]
        
        if action_type == "shift":
            step["Action"] = "Shift"
            stack.append(value)
            index += 1
        elif action_type == "reduce":
            prod_index = value
            lhs, rhs = productions[prod_index]
            step["Action"] = "Reduce ({0} -> {1})".format(lhs, " ".join(rhs))
            for _ in range(len(rhs)):
                stack.pop()
            current_state = stack[-1]
            stack.append(goto[(current_state, lhs)])
        elif action_type == "accept":
            step["Action"] = "Accept"
            steps.append(step)
            break
        
        steps.append(step)
    
    return steps

def print_states_table(states, productions):
    print("\nCLR(1) States:")
    print("| State | Items                                      |")
    print("|-------|--------------------------------------------|")
    for i, state in enumerate(states):
        items_str = ", ".join(["[{0} -> {1}, {2}]".format(
            productions[p][0],
            " ".join(productions[p][1][:d] + ["."] + productions[p][1][d:] if d < len(productions[p][1]) else productions[p][1] + ["."]),
            l
        ) for p, d, l in state])
        print("| I{0:<4} | {1:<42} |".format(i, items_str))

def print_parsing_table(action, goto, terminals, non_terminals):
    print("\nCLR(1) Parsing Table:")
    header = "| State | " + " | ".join(["Action: {0:<2}".format(t) for t in sorted(terminals)]) + " | " + " | ".join(["Goto: {0:<2}".format(nt) for nt in sorted(non_terminals)]) + " |"
    print(header)
    print("|-------|" + "---|" * (len(terminals) + len(non_terminals)) + "|")
    states_count = max(max(action.keys(), default=(-1, ""))[0], max(goto.keys(), default=(-1, ""))[0]) + 1
    for i in range(states_count):
        row = "| {0:<5} | ".format(i)
        for t in sorted(terminals):
            if (i, t) in action:
                act, val = action[(i, t)]
                if act == "shift":
                    row += "S{0:<5} | ".format(val)
                elif act == "reduce":
                    row += "R{0:<5} | ".format(val)
                elif act == "accept":
                    row += "Accept | "
                else:
                    row += "      | "
            else:
                row += "      | "
        for nt in sorted(non_terminals):
            if (i, nt) in goto:
                row += "{0:<5} | ".format(goto[(i, nt)])
            else:
                row += "      | "
        print(row)

def print_parse_table(steps):
    print("\nParsing Steps:")
    print("| Step | Stack       | Input   | Action            |")
    print("|------|-------------|---------|-------------------|")
    for step in steps:
        print("| {0:<4} | {1:<11} | {2:<7} | {3:<17} |".format(step["Step"], step["Stack"], step["Input"], step["Action"]))

if __name__ == "__main__":
    grammar = ["S -> C C", "C -> c C", "C -> d"]
    productions = augment_grammar(parse_grammar(grammar))
    action, goto, productions, states = compute_clr_parser(grammar)
    
    print_states_table(states, productions)
    non_terminals, terminals = get_symbols(productions)
    print_parsing_table(action, goto, terminals, non_terminals)
    
    input_string = "c d d"
    steps = parse_input(action, goto, productions, input_string)
    print("\nParsing '{0}':".format(input_string))
    print_parse_table(steps)