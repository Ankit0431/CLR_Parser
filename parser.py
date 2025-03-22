def parse_grammar(input_strings):
    """
    Parse grammar strings into a list of (LHS, RHS) tuples.
    
    Args:
        input_strings (list): List of grammar rules as strings, e.g., ["S -> CC", "C -> cC"].
    Returns:
        list: List of tuples, e.g., [("S", ["C", "C"]), ("C", ["c", "C"])].
    """
    productions = []
    for s in input_strings:
        lhs, rhs_str = s.split(" -> ")
        rhs = list(rhs_str)  # Split RHS into individual symbols
        productions.append((lhs, rhs))
    return productions

def augment_grammar(productions):
    """
    Augment the grammar by adding S' -> S, where S is the original start symbol.
    
    Args:
        productions (list): List of (LHS, RHS) tuples.
    Returns:
        list: Augmented list of productions.
    """
    start_symbol = productions[0][0]
    augmented = [("S'", [start_symbol])] + productions
    return augmented

def get_symbols(productions):
    """
    Identify non-terminals and terminals in the grammar.
    
    Returns:
        set, set: Non-terminals and terminals.
    """
    non_terminals = set(lhs for lhs, rhs in productions)
    all_symbols = set(symbol for lhs, rhs in productions for symbol in rhs)
    terminals = all_symbols - non_terminals
    terminals.add("$")  # Add end-of-input marker
    return non_terminals, terminals

def compute_nullable(productions, non_terminals):
    """
    Compute which non-terminals are nullable (can derive the empty string).
    
    Returns:
        dict: Mapping of non-terminals to True/False indicating nullability.
    """
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
    """
    Compute FIRST sets for all symbols.
    
    Returns:
        dict: Mapping of symbols to their FIRST sets.
    """
    first = {symbol: set() for symbol in non_terminals.union(terminals)}
    # Initialize FIRST for terminals
    for t in terminals:
        first[t].add(t)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in productions:
            if not rhs:
                continue
            for symbol in rhs:
                if symbol in terminals:
                    if symbol not in first[lhs]:
                        first[lhs].add(symbol)
                        changed = True
                    break
                elif symbol in non_terminals:
                    for t in first[symbol]:
                        if t not in first[lhs]:
                            first[lhs].add(t)
                            changed = True
                    if not nullable[symbol]:
                        break
    return first

def first_of_sequence(sequence, lookahead, first, nullable, terminals, non_terminals):
    """
    Compute FIRST(βa) for a sequence β followed by lookahead a.
    
    Returns:
        set: FIRST set of the sequence with lookahead.
    """
    result = set()
    for symbol in sequence:
        if symbol in terminals:
            result.add(symbol)
            return result
        elif symbol in non_terminals:
            result.update(first[symbol])
            if not nullable[symbol]:
                return result
    result.add(lookahead)  # All symbols in sequence are nullable
    return result

def closure(items, productions, first, nullable, terminals, non_terminals):
    """
    Compute the closure of a set of LR(1) items.
    
    Args:
        items (set): Set of (prod_index, dot_position, lookahead) tuples.
    Returns:
        set: Closed set of LR(1) items.
    """
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

def goto(items, symbol, productions, first, nullable, terminals, non_terminals):
    """
    Compute the Goto set for a set of items and a symbol X.
    
    Returns:
        set: Set of LR(1) items after moving the dot past the symbol.
    """
    J = set()
    for prod_index, dot_position, lookahead in items:
        prod = productions[prod_index]
        rhs = prod[1]
        if dot_position < len(rhs) and rhs[dot_position] == symbol:
            new_item = (prod_index, dot_position + 1, lookahead)
            J.add(new_item)
    return closure(J, productions, first, nullable, terminals, non_terminals)

def build_dfa(productions, first, nullable, terminals, non_terminals):
    """
    Build the collection of LR(1) sets of items (DFA states).
    
    Returns:
        list, dict: List of states and transitions dictionary.
    """
    initial_item = (0, 0, "$")  # [S' -> .S, $]
    I0 = closure({initial_item}, productions, first, nullable, terminals, non_terminals)
    states = [I0]
    state_dict = {frozenset(I0): 0}
    transitions = {}  # (state_index, symbol) -> next_state_index
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
    """
    Construct the ACTION and GOTO tables.
    
    Returns:
        dict, dict: ACTION and GOTO tables.
    """
    action = {}  # (state, terminal) -> ("shift", state) | ("reduce", prod_index) | "accept"
    goto = {}    # (state, non_terminal) -> state
    
    for i, state in enumerate(states):
        # Shift actions
        for t in terminals:
            if (i, t) in transitions:
                action[(i, t)] = ("shift", transitions[(i, t)])
        
        # Reduce and accept actions
        for prod_index, dot_position, lookahead in state:
            prod = productions[prod_index]
            rhs = prod[1]
            if dot_position == len(rhs):
                if prod_index == 0 and lookahead == "$":  # [S' -> S., $]
                    action[(i, "$")] = "accept"
                else:
                    action[(i, lookahead)] = ("reduce", prod_index)
        
        # Goto transitions
        for nt in non_terminals:
            if (i, nt) in transitions:
                goto[(i, nt)] = transitions[(i, nt)]
    
    return action, goto

def compute_clr_parser(input_grammar):
    """
    Main function to compute CLR parsing tables from a list of grammar strings.
    
    Args:
        input_grammar (list): List of grammar strings, e.g., ["S -> CC", "C -> cC", "C -> d"].
    Returns:
        dict, dict, list: ACTION table, GOTO table, and list of DFA states.
    """
    # Parse the input grammar strings
    productions = parse_grammar(input_grammar)
    productions = augment_grammar(productions)
    non_terminals, terminals = get_symbols(productions)
    nullable = compute_nullable(productions, non_terminals)
    first = compute_first(productions, non_terminals, terminals, nullable)
    states, transitions = build_dfa(productions, first, nullable, terminals, non_terminals)
    action, goto = build_parsing_table(states, transitions, productions, terminals, non_terminals)
    return action, goto, states

# Example usage
if __name__ == "__main__":
    grammar = ["S -> CC", "C -> cC", "C -> d"]
    action, goto, states = compute_clr_parser(grammar)
    
    print("States:")
    for i, state in enumerate(states):
        print(f"I{i}: {state}")
    print("\nACTION table:")
    for key, value in action.items():
        print(f"ACTION[{key[0]}, {key[1]}] = {value}")
    print("\nGOTO table:")
    for key, value in goto.items():
        print(f"GOTO[{key[0]}, {key[1]}] = {value}")