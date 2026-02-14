from lark import Lark, Transformer, v_args, Tree

grammar = """
    ?start: expr
    
    ?expr: "F" bound? "(" prob_comp ")" -> eventually
         | "G" bound? "(" prob_comp ")" -> globally
         | prob_comp
    
    bound: "<=" NUMBER -> bound
    
    ?prob_comp: "prob" "(" basis ")" COMPARISON NUMBER -> prob_pred
    
    basis: "|" BINARY ">" -> basis_state
    
    COMPARISON: ">" | "<" | ">=" | "<=" | "=="
    NUMBER: /[0-9]+(\\.[0-9]+)?/
    BINARY: /[01]+/
    
    %import common.WS
    %ignore WS
"""

@v_args(inline=True)
class LTLTransformer(Transformer):
    def eventually(self, *args):
        # Handle both F(pred) and F<=k(pred)
        if len(args) == 1:
            # No bound: F(pred)
            pred = args[0]
            op = 'F'
        else:
            # With bound: F<=k(pred)
            bound_val, pred = args
            op = f'F<={bound_val}'
        return {'operator': op, 'predicate': pred}
    
    def globally(self, *args):
        if len(args) == 1:
            pred = args[0]
            op = 'G'
        else:
            bound_val, pred = args
            op = f'G<={bound_val}'
        return {'operator': op, 'predicate': pred}
    
    def bound(self, num):
        return int(float(num))  # Convert to int for bound
    
    def prob_pred(self, basis, comp, num):
        return {
            'type': 'probability',
            'basis': str(basis),
            'comparison': str(comp),
            'threshold': float(num)
        }
    
    def basis_state(self, bits):
        return str(bits)

def parse_ltl(spec_str: str) -> dict:
    parser = Lark(grammar, start='start', parser='lalr', transformer=LTLTransformer())
    return parser.parse(spec_str)
