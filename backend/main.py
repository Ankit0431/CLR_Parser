from flask import Flask, request, jsonify
from collections import defaultdict
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://clr-parser-seven.vercel.app/"}})

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

def compute_first(productions, non_terminals, terminals):
    first = {symbol: set() for symbol in non_terminals.union(terminals)}
    for t in terminals:
        first[t].add(t)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in productions:
            first_set = set()
            for symbol in rhs:
                first_set.update(first[symbol] - {""})
                if "" not in first[symbol]:
                    break
            else:
                first_set.add("")
            if not first_set.issubset(first[lhs]):
                first[lhs].update(first_set)
                changed = True
    return first

def closure(items, productions, first, non_terminals):
    I = set(items)
    changed = True
    while changed:
        changed = False
        new_items = set()
        for prod_index, dot_pos, lookahead in I:
            lhs, rhs = productions[prod_index]
            if dot_pos < len(rhs) and rhs[dot_pos] in non_terminals:
                next_symbol = rhs[dot_pos]
                beta = rhs[dot_pos + 1:]
                first_beta = set()
                for sym in beta:
                    first_beta.update(first[sym] - {""})
                    if "" not in first[sym]:
                        break
                else:
                    first_beta.add(lookahead)
                for j, (nt, rule_rhs) in enumerate(productions):
                    if nt == next_symbol:
                        for la in first_beta:
                            new_item = (j, 0, la)
                            if new_item not in I:
                                new_items.add(new_item)
                                changed = True
        I.update(new_items)
    return I

def goto(items, symbol, productions, first, non_terminals):
    J = set()
    for prod_index, dot_pos, lookahead in items:
        lhs, rhs = productions[prod_index]
        if dot_pos < len(rhs) and rhs[dot_pos] == symbol:
            new_item = (prod_index, dot_pos + 1, lookahead)
            J.add(new_item)
    return closure(J, productions, first, non_terminals)

def build_dfa(productions, first, non_terminals):
    initial_item = (0, 0, "$")
    I0 = closure({initial_item}, productions, first, non_terminals)
    states = [I0]
    state_dict = {frozenset(I0): 0}
    transitions = {}
    to_process = [0]
    while to_process:
        current = to_process.pop(0)
        current_state = states[current]
        symbols = non_terminals.union({t for _, rhs in productions for t in rhs})
        for symbol in symbols:
            next_state = goto(current_state, symbol, productions, first, non_terminals)
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

def build_parsing_table(states, transitions, productions, non_terminals):
    action = defaultdict(list)  # Changed to list to store multiple actions
    goto = {}
    terminals = {t for _, rhs in productions for t in rhs if t not in non_terminals}.union({"$"})
    
    for i, state in enumerate(states):
        # Process shifts first
        for t in terminals:
            if (i, t) in transitions:
                action[(i, t)].append(("shift", transitions[(i, t)]))
        
        # Process reduces and accept
        for prod_index, dot_pos, lookahead in state:
            lhs, rhs = productions[prod_index]
            if dot_pos == len(rhs):
                if prod_index == 0 and lookahead == "$":
                    action[(i, "$")].append("accept")
                else:
                    action[(i, lookahead)].append(("reduce", prod_index))
        
        # Process goto transitions
        for nt in non_terminals:
            if (i, nt) in transitions:
                goto[(i, nt)] = transitions[(i, nt)]
    
    return action, goto

def format_production(prod_index, dot_pos, productions):
    lhs, rhs = productions[prod_index]
    rhs_with_dot = rhs[:dot_pos] + ['.'] + rhs[dot_pos:]
    return f"{lhs} -> {' '.join(rhs_with_dot)}"

def compute_clr_parser(input_grammar):
    productions = parse_grammar(input_grammar)
    productions = augment_grammar(productions)
    non_terminals = {lhs for lhs, _ in productions}
    terminals = {t for _, rhs in productions for t in rhs if t not in non_terminals}
    first = compute_first(productions, non_terminals, terminals)
    states, transitions = build_dfa(productions, first, non_terminals)
    action, goto = build_parsing_table(states, transitions, productions, non_terminals)
    return action, goto, states, productions, terminals

def make_json_serializable(obj, productions=None):
    if isinstance(obj, set):
        if productions and all(isinstance(item, tuple) and len(item) == 3 for item in obj):
            # Format states with productions
            return [{
                'production': format_production(item[0], item[1], productions),
                'lookahead': item[2]
            } for item in sorted(obj)]
        return sorted(list(obj))
    elif isinstance(obj, dict):
        return {str(k): make_json_serializable(v, productions) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item, productions) for item in obj]
    elif isinstance(obj, tuple):
        return [make_json_serializable(item, productions) for item in obj]
    return obj

@app.route('/parse', methods=['POST'])
def parse_grammar_route():
    try:
        data = request.get_json()
        grammar = data.get('grammar', '').strip().split('\n')
        if not grammar or all(not rule.strip() for rule in grammar):
            return jsonify({'error': 'No grammar rules provided'}), 400
        grammar = [rule.strip() for rule in grammar if rule.strip()]
        
        action, goto, states, productions, terminals = compute_clr_parser(grammar)
        
        # Format action table for all terminals in same row
        formatted_action = {}
        for (state, symbol), actions in action.items():
            if str(state) not in formatted_action:
                formatted_action[str(state)] = {t: [] for t in terminals.union({"$"})}
            formatted_action[str(state)][symbol] = actions
        
        response = {
            'action': make_json_serializable(formatted_action),
            'goto': make_json_serializable(goto),
            'states': make_json_serializable(states, productions),
            'productions': [f"{lhs} -> {' '.join(rhs)}" for lhs, rhs in productions]
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host = '0.0.0.0', port=5000)