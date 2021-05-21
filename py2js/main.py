from .transpiler import transpile

# python_parser = Lark.open()

# code = """
# a = 1 # Hello
# class A:
# 	def __init__(self):
# 		self.a = 1

# 	def bla(self):
# 		return self.a            # another comment

# while False:
# 	pass

# a = A()
# x = b = a.bla()
# b += 10
# for i in range(3):
# 	if i==0:
# 		print(b)
# 	elif i==1:
# 		print("true")
# 		print((1+2) / 3)
# 	else:
# 		assert False, "lala"

# comprehension = [x+'map' for x in range(10) if x!='if']
# print(comprehension)

# def dec(x):
# 	return x

# @dec
# def bla(z):
# 	return z+2
# """

# code = open(__file__).read() + '\n'
# code = open('c:/code/lark/lark/tree.py').read() + '\n'
# code = open('c:/code/lark/lark/grammar.py').read() + '\n'
# code = open('c:/code/lark/lark/common.py').read() + '\n'
# code = open('c:/code/lark/lark/exceptions.py').read() + '\n'
# code = open('c:/code/lark/lark/visitors.py').read() + '\n'

# tree = ast.parse(code)

# code = """
# x = [(x,y) 
#   for x in range(10)
#   for y in range(x)
#   if x+y==5
# ]
# """

code = """
try:
	bla
except NameError:
	console.log('no such name')
else:
	console.log('actually its okay')
"""

# code = """
# def f(*args):
# 	return args

# print(f(1, 2))
# """


PRETTIER = r'C:\Users\erez\AppData\Roaming\npm\prettier.cmd'


lib = '''
function range(start, end) {
    if (end === undefined) {
      end = start;
      start = 0;
    }
    res = []
    for (let i=start; i<end; i++) res.push(i);
    return res
};

String.prototype.format = function() {
    var counter = 0;
    var args = arguments;

    return this.replace(/%[sr]/g, function() {
        return args[counter++];
    });
};
'''

def main():
	from subprocess import check_output
	t = transpile(code)
	with open('tmp.js', 'w') as f:
		f.write(t)
	res = check_output([PRETTIER, 'tmp.js'])
	print(lib + res.decode())

main()