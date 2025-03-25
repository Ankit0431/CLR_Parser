from flask import Flask, request, jsonify
from collections import defaultdict
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from React frontend

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
                if prod_index == 0 and lookahead == "$":
                    action[(i, "$")] = "accept"
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
    return action, goto, states

# Helper function to convert sets to lists for JSON serialization
def make_json_serializable(obj):
    if isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        return {str(k): make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [make_json_serializable(item) for item in obj]
    return obj

# Flask route for parsing
@app.route('/parse', methods=['POST'])
def parse_grammar_route():
    try:
        data = request.get_json()
        grammar = data.get('grammar', '').strip().split('\n')
        
        if not grammar or all(not rule.strip() for rule in grammar):
            return jsonify({'error': 'No grammar rules provided'}), 400
            
        # Clean and validate grammar rules
        grammar = [rule.strip() for rule in grammar if rule.strip()]
        for rule in grammar:
            if ' -> ' not in rule:
                return jsonify({'error': f'Invalid rule format: {rule}'}), 400
                
        action, goto, states = compute_clr_parser(grammar)
        
        # Convert response to JSON-serializable format
        response = {
            'action': make_json_serializable(action),
            'goto': make_json_serializable(goto),
            'states': make_json_serializable(states)
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)