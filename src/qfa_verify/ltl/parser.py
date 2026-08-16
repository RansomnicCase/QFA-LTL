from lark import Lark, Transformer, v_args, Tree

grammar = """
    ?start: expr
    
    ?expr: "F" bound? "(" prob_comp ")" -> eventually
         | "G" bound? "(" prob_comp ")" -> globally
         | prob_comp
    
    bound: "<=" NUMBER -> bound
    
    ?prob_comp: sum_prob COMPARISON NUMBER -> prob_pred
    
    ?sum_prob: prob_term ("+" prob_term)*
    
    prob_term: "prob" "(" basis ")" -> prob_basis
    
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
    
    def prob_pred(self, *args):
        # args = [basis..., comparison, number]
        comp = args[-2]
        num = args[-1]
        bases = list(args[:-2])
        return {
            'type': 'probability',
            'bases': bases,
            'basis': bases[0] if len(bases) == 1 else None,  # back-compat single-basis accessor
            'comparison': str(comp),
            'threshold': float(num)
        }
    
    def prob_basis(self, basis):
        return str(basis)
    
    def basis_state(self, bits):
        return str(bits)

def parse_ltl(spec_str: str) -> dict:
    parser = Lark(grammar, start='start', parser='lalr', transformer=LTLTransformer())
    return parser.parse(spec_str)
