from typing import List, Optional

from runtype import Dispatch, assert_isa
from lark import Transformer, Visitor, v_args, Tree, Token

from .python_parser import parse


dsp = Dispatch()

def _args_wrapper(f, _data, children, meta):
    "Create meta with 'code' from transformer"
    res = f(*children)

    header_comments = getattr(meta, 'header_comments', None)
    if header_comments:
    	return '\n'.join('//' + h.lstrip()[1:] for h in header_comments) + '\n' + res
    inline_comment = getattr(meta, 'inline_comment', None)
    if inline_comment:
    	c = inline_comment.lstrip()
    	assert c.startswith('#'), c
    	res += "    //" + c[1:] + '\n'
    return res

as_args = v_args(inline=False)

VAR_TRANSLATION = {
	'print': 'console.log',
	'self': 'this',
	'append': 'push',
	'Exception': 'Error',
	'NameError': 'ReferenceError',
}


@v_args(wrapper=_args_wrapper)
class ToJs(Transformer):
	NAME = number = str
	# string = str
	def string(self, s):
		if s.startswith('b'):
			# TODO special handling?
			return s[1:]
		return str(s)

	def LONG_STRING(self, s):
		assert s.startswith(('"""', "'''")), s
		assert s.endswith(('"""', "'''")), s
		return '`%s`' % s[3:-3].replace('`', '``')

	def var(self, name):
		return VAR_TRANSLATION.get(name, name)

	def getattr(self, obj, attr):
		attr = VAR_TRANSLATION.get(attr, attr)
		return f'{obj}.{attr}'

	def typed_param(self, name, type):
		assert not type 	# tmp
		return name

	@as_args
	def arguments(self, args):
		assert_isa(args, List[Optional[str]])
		return ', '.join(p for p in args if p)

	def funccall(self, obj, arguments):
		if obj.isupper():		# XXX hack! Use type information
			obj = "new " + obj

		return f'{obj}({arguments or ""})'

	def instanceof(self, inst, type_):
		return f'({inst} instanceof {type_})'

	@as_args
	def comp_op(self, op):
		return ' '.join(op)

	@as_args
	def comparison(self, args):
		# TODO comparison uses __eq__ sometimes
		if len(args) > 3:
			breakpoint()
		# TODO code is probably wrong
		comps = []
		for i in range(0, len(args)-1, 2):
			a, op, b = args[i:i+3]
			if op == 'is':
				op = '=='
			elif op == 'is not':
				op = '!='

			if op == 'not in':
				comps += [f'!({a} in {b})']
			else:
				comps += [f'({a} {op} {b})']
		return ' and '.join(comps)


	@as_args
	def _expr(self, args):
		assert_isa(args, List[str])
		return '(%s)' % ' '.join(args)

	arith_expr = _expr
	term = _expr

	def factor(self, a, b):
		return f'{a}{b}'

	def test(self, expr, cond, else_):
		return f'({cond}?{expr}:{else_})'

	@as_args
	def and_test(self, args):
		assert_isa(args, List[str])
		return '(%s)' % ' && '.join(args)

	@as_args
	def or_test(self, args):
		assert_isa(args, List[str])
		return '(%s)' % ' || '.join(args)


	@as_args
	def and_expr(self, args):
		assert_isa(args, List[str])
		return '(%s)' % ' & '.join(args)

	def not_test(self, value):
		return '(!%s)' % value

	def const_true(self):
		return 'true'

	def const_false(self):
		return 'false'

	def const_none(self):
		return 'null'

	def starparams(self, name):
		return '...' + name

	def starargs(self, name):
		return '...' + name

	@as_args
	def testlist_star_expr(self, args):
		if len(args) == 1:
			return args[0]

		return '[%s]' % ', '.join(args)

	@as_args
	def inlineargs(self, args):
		# XXX not exactly correct
		return ', '.join(f'*{a}' for a in args)

	@as_args
	def starargs(self, args):
		return ', '.join(filter(None, args))

	def argvalue(self, key, value):
		return f'{key}={value}'

	def getitem(self, obj, subscript):
		return f'{obj}[{subscript}]'

	def list_comp(self, x):
		return x

	def varargslist(self, x):
		# TODO
		return x

	def lambdef(self, vars, body):
		return f'(({vars}) => {body})'

	def dotted_name(self, *names):
		return '.'.join(names)

	def paramvalue(self, param, value):
		return f'{param}={value}'


	@as_args
	def tuple(self, elems):
		inner =  ', '.join(elems)
		return f"[{inner or ''}]"

	exprlist = tuple

	def list(self, inner):
		return f"[{inner or ''}]"

	def dict(self, inner):
		return f"{{{inner or ''}}}"


	def yield_expr(self, expr):
		return 'yield ' + expr

	def yield_stmt(self, expr):
		return expr + ';'


	def list_comprehension(self, comp):
		return comp

	def dict_comprehension(self, comp):
		return f'new Map({comp})'

	def set_comprehension(self, comp):
		return f'new Set({comp})'

	@as_args
	def lambda_params(self, params):
		return ', '.join(filter(None, params))


	# Statements

	def expr_stmt(self, stmt):
		return stmt

	def return_stmt(self, value):
		return f'return {value};'

	def continue_stmt(self):
		return 'continue'

	def break_stmt(self):
		return 'break'

	@v_args(meta=True, inline=False)
	def assign(self, args, meta):
		assert_isa(args, List[str])
		# TODO let
		if args[0] == '__slots__' or args[0].startswith('__serialize_'):
			return ''

		if getattr(meta, 'in_class', False):
			var, value = args
			return f"get {var}() {{ return {value}; }}"

		let = 'let ' if getattr(meta, 'new_var', False) else ''
		return let + ' = '.join(args);

	def assign_stmt(self, a):
		return a


	augassign_op = str
	def augassign(self, target, op, value):
		return f'{target} {op} {value};'

	def elif_(self, cond, stmts):
		return f'else if ({cond}) {{\n{stmts}}}\n'

	@as_args
	def elifs(self, elifs):
		return '\n'.join(elifs)

	def if_stmt(self, cond, then, elifs, else_):
		s = f'if ({cond}) {{\n{then}}}\n'
		if elifs:
			s += elifs
		if else_:
			s += 'else {\n' + else_ + '}'
		return s

	def pass_stmt(self):
		return ''

	def while_stmt(self, cond, body, else_):
		assert not else_
		return f'while ({cond}) {{\n{body}}}\n'

	def for_stmt(self, var, seq, body, else_):
		assert not else_
		return f'for (let {var} of {seq}) {{\n{body}}}\n'

	def assert_stmt(self, cond, msg):
		if msg:
			return f'console.assert({cond}, {msg})'
		return f'console.assert({cond})'

	def raise_stmt(self, expr, orig=None):
		return f'throw {expr}'

	@as_args
	def suite(self, stmts):
		assert_isa(stmts, List[str])
		return '\n'.join(stmts)

	@as_args
	def file_input(self, nodes):
		assert_isa(nodes, List[str])

		return '\n'.join(nodes)

	def import_stmt(self, *args):
		return ''



	# Definitions
	@as_args
	def starparams(self, args):
		return '...' + ', '.join(filter(None, args))


	@as_args
	def parameters(self, params):
		assert_isa(params, List[Optional[str]])
		if params and params[0] == 'self':
			params = params[1:]			
		return '(%s)' % ', '.join(p for p in params if p)

	def classdef(self, name, superclasses, suite):
		superclass = ''
		if superclasses:
			superclass = ' extends ' + superclasses

		return f'\n\nclass {name}{superclass} {{\n{suite}}}\n'

	@v_args(meta=True, inline=True)
	def funcdef(self, meta, name, params, return_type, suite):
		assert not return_type
		# Only if method!

		s = ''
		if name == '__init__':
			name = 'constructor'
			# suite = 'super();\n' + suite	# TODO find calls to super?
		else:
			if not getattr(meta, 'in_class', False):
				s = 'function '

			if getattr(meta, 'is_generator', False):
				s += '* '

		return f'\n{s}{name}{params} {{\n{suite}}}\n'

	@as_args
	def except_clauses(self, excepts):
		ifs = []
		for exc_type, name, code  in excepts:
			if_text = f'if (e instanceof {exc_type}) {{\n'
			if name:
				if_text += f'{name}=e;' 
			if_text += f'\n{code}}}'
			ifs.append(if_text)

		assert ifs
		return ifs

	def except_clause(self, *args):
		return args

	def try_stmt(self, body, except_, else_, finally_):
		assert finally_ is None
		assert except_
		ifs = ' else '.join(except_)

		set_exc = 'exc=e;' if else_ else ''
		try_ = f'try{{\n{body}}}\ncatch (e){{{set_exc}{ifs}}}'
		if else_:
			try_ = 'exc=null;' + try_ + f'if(!exc) {{{else_}}}'

		return try_


	def del_stmt(self, vars):
		return ''


	def decorator(self, name, arguments):
		if name == 'property':
			return ''			# TODO property
		if arguments:
			return f'@{name}({arguments})'
		return f'@{name}'

	@as_args
	def decorators(self, decs):
		return '\n'.join(decs)

	@v_args(meta=True, inline=True)
	def decorated(self, meta, decs, def_):
		return f'{decs}{def_}'





class Parent(Visitor):
    # def __default__(self, tree):
    #     for subtree in tree.children:
    #         if isinstance(subtree, Tree):
    #             assert not hasattr(subtree, 'parent'), subtree
    #             subtree.parent = tree
    pass

class PrepareAst(Visitor):
	def getitem(self, tree):
		obj, subscript = tree.children
		if subscript.data == 'slice':
			slice_func = Tree('getattr', [obj, 'slice'])
			tree.data = 'funccall'
			tree.children = [slice_func, Tree('arguments', subscript.children)]

	def classdef(self, tree):
		name, superclasses, elems = tree.children
		if superclasses:
			sc_list = superclasses.children
			for i, sc in reversed(list(enumerate(superclasses.children))):
				if sc_list[i] in (Tree('var', ['object']), Tree('var', ['ValueError'])):
					del sc_list[i]
			if len(sc_list) > 1:
				# raise NotImplementedError(sc_list)
				sc_list = sc_list[:1]
			superclasses.children = sc_list

		elems = elems.children
		if elems:
			if elems[0].data == 'expr_stmt':
				s ,= elems[0].find_data('string')
				s ,= s.children
				assert s.startswith(('"', "'"))
				assert s.endswith(('"', "'"))
				elems[0].children = ['/*\n%s\n*/\n' % s[3:-3]]

			# if isinstance(elems[0], Token) and elems[0].type == 'LONG_STRING':

		for e in elems:
			if e.data == 'funcdef':
				e.meta.in_class = True
			elif e.data == 'decorated':
				_decs, obj = e.children
				assert obj.data == 'funcdef', obj
				obj.meta.in_class = True
			elif e.data == 'assign_stmt':
				assign ,= e.children
				assign.meta.in_class = True
			elif e.data in ('expr_stmt', 'pass_stmt'):
				pass
			else:
				assert False, e

	def funcdef(self, tree):
		if any(tree.find_pred(lambda n: n.data in ('yield_expr', 'yield_from'))):
			tree.meta.is_generator = True


	def assign(self, tree):
		lval = tree.children[0]
		if not any(lval.find_pred(lambda n: n.data in ('getattr', 'getitem'))):
			tree.meta.new_var = True



# 		return 'catch '
# except_clause: "except" [test ["as" NAME]] ":" suite


@v_args(inline=True)
class PrepareAst2(Transformer):
	def comprehension(self, test, comp_fors, comp_if):
		# a for b in c if d 
		#  =>
		# c.filter((b) => d).map((b) => a)

		if test.data == 'key_value':
			# Dict comprehension
			key, value = test.children
			test = Tree('tuple', [key, value])

		# assert len(comp_fors.children) == 1
		assert comp_fors.data == 'comp_fors'
		comp_for = comp_fors.children[-1]
		_async, var, expr = comp_for.children
		assert _async is None, "Not implemented"


		if comp_if:
			filter_method = Tree('getattr', [expr, 'filter'])
			filter_lambda = Tree('lambdef', [Tree('varargslist', [var]), comp_if])
			expr = Tree('funccall', [filter_method, filter_lambda])

		# List comprehension
		map_method = Tree('getattr', [expr, 'map'])
		map_lambda = Tree('lambdef', [Tree('varargslist', [var]), test])
		expr = Tree('funccall', [map_method, map_lambda])

		if len(comp_fors.children) > 1:
			for comp_for in comp_fors.children[:-1]:
				_async, var, subexpr = comp_for.children
				assert _async is None, "Not implemented"
				map_method = Tree('getattr', [subexpr, 'map'])
				map_lambda = Tree('lambdef', [Tree('varargslist', [var]), expr])
				expr = Tree('funccall', [map_method, map_lambda])

			concat_method = Tree('getattr', [Tree('tuple', []), 'concat'])
			return Tree('funccall', [concat_method, Tree('kwargs', [expr])])


		return expr

	def funccall(self, obj, arguments):
		if obj.data == 'var':
			if obj.children == ['isinstance']:
				assert arguments.data == 'arguments'
				return Tree('instanceof', arguments.children)
			elif obj.children == ['len']:
				a ,= arguments.children
				return Tree('getattr', [a, 'length'])
			elif obj.children == ['id']:
				a ,= arguments.children
				return a
			elif obj.children == ['list']:
				a ,= arguments.children
				return Tree('funccall', [Tree('var', ['Array.from']), a])
			elif obj.children == ['reversed']:
				a ,= arguments.children
				arr_copy = Tree('funccall', [Tree('getattr', [a, 'slice']), None])
				return Tree('funccall', [Tree('getattr', [arr_copy, 'reverse']), None])
			elif obj.children == ['OrderedDict']:
				return Tree('funccall', ['new Map', arguments])
			elif obj.children == ['getattr']:
				a, b, *c = arguments.children

				getitem = Tree('getitem', [a, b])
				if c:
					return Tree('or_test', [getitem] + c)
				return getitem


		return Tree('funccall', [obj, arguments])

	def term(self, a, op, b):
		if op == '%':
			fmt = Tree('getattr', [a, 'format'])
			if b.data == 'tuple':
				args = Tree('arguments', b.children)
			else:
				args = b

			return Tree('funccall', [fmt, args])

		return Tree('term', [a, op, b])



def transpile(python_code):
	tree = parse(python_code)
	tree = PrepareAst2().transform(tree)
	PrepareAst().visit(tree)
	return ToJs().transform(tree)