# coding=utf-8
from antlr4 import *
from parse.CoolLexer import *
from parse.CoolParser import *
from parse.CoolListener import *
from CodeGenListener import *

import sys
from string import Template
from templates import *

classToID = {}

INT_TAG = 2
BOOL_TAG = 3
STRING_TAG = 4

class Output:
    def __init__(self):
        self.accum = ''

    def p(self, *args):
        if len(args) == 1:
            self.accum += '%s:\n' % args[0]
            return

        r = '    %s    ' % args[0]

        for a in args[1:-1]:
            r += ' %s' % str(a)

        if type(args[-1]).__name__ != 'int' and args[-1][0] == '#':
            for i in range(64 - len(r)):
                r += ' '
        r += str(args[-1])

        self.accum += r + '\n'

    def out(self):
        return self.accum


def global_data(o):
    k = dict(intTag=INT_TAG, boolTag=BOOL_TAG, stringTag=STRING_TAG)
    o.accum = gdStr1 + gdTpl1.substitute(k) + gdStr2


def constants(o):
    """
    1. Determinar literales string
        1.1 Obtener lista de literales (a cada una asignar un índice) + nombres de las clases
        1.2 Determinar constantes numéricas necesarias
        1.3 Reemplazar en el template:
            - tag
            - tamanio del objeto: [tag, tamanio, ptr al dispTab, ptr al int, (len(contenido)+1)%4] = ?
                (el +1 es por el 0 en que terminan siempre)
            - índice del ptr al int
            - valor (el string)
    2. Determinar literales enteras
        2.1 Literales necesarias en el punto 1
        2.2 + constantes en el código fuente
        2.3 Reemplazar en el template:
            - tag
            - tamanio del objeto: [tag, tamanio, ptr al dispTab y contenido] = 4 words
            - valor
    """

    #Strings

    idxStr = 3 + len(constantesString) - 1


    #Id para los enteros ya dentro del pool
    idInt = -1

    print("Attributes")
    for a in classToAttribute:
        print(a)
        print(classToAttribute[a])
        print("\n")


    print("Methods")
    for m in classToMethod:
        print(m)
        print(classToMethod[m])
        print("\n")

    print("Integer Constants")
    for c in constantesInt:
        print(c)

    print("Trolol")

    print("String Constants")
    for c in constantesString:
        print(c)


    for constante in constantesString:
        length = str(len(constante))

        #print(constant)
        #print(s)
        #print(str(s))
        #print(constant)
        #print(length)
        #print("...")

        #Si ya está el valor en el pool, optimizar y usar el que ya existe
        # Si no, agregarlo
        if length not in constantesInt:
            constantesInt.append(length)
            idInt = len(constantesInt) - 1

        else:
            idInt = constantesInt.index(length);

        #Número de bytes del align
        padding = 0;

        if (len(constante) + 1) % 4 != 0:
            padding = 4 - ((len(constante) + 1) % 4)

        size = ((len(constante) + 1 + padding) / 4) + 4
        o.accum += cTplStr.substitute(idx=idxStr, tag=STRING_TAG, size=size, sizeIdx=idInt, align=padding, value=constante)

        #Como la estructura classNames tiene los nombres de las clases, asociarlos con su índice en classToID
        if constante in classNames:
            classToID[constante] = idxStr

        idxStr -= 1

    extras = ["\\n", "<basic_class>", "--filename--"]

    #Valores base
    for e in extras:
        extraLength = len(e)
        # Si ya está el valor en el pool, optimizar y usar el que ya existe
        # Si no, agregarlo
        if extraLength not in constantesInt:
            constantesInt.append(extraLength)
            idInt = len(constantesInt) - 1

        else:
            idInt = constantesInt.index(extraLength);

        o.accum += cTplStr.substitute(idx=idxStr, tag=STRING_TAG, size=8, sizeIdx=idInt, align=2,
                                      value=e)
        idxStr -= 1

    #Enteros
    idxInt = len(constantesInt) - 1
    for c in constantesInt:
        o.accum += cTplInt.substitute(idx=idxInt, tag=INT_TAG, value=c)
        idxInt -= 1

    # Siempre incluir los bool
    o.accum += boolStr


def tables(o):
    """
    1. class_nameTab: tabla para los nombres de las clases en string
        1.1 Los objetos ya fueron generados arriba
        1.2 El tag de cada clase indica el desplazamiento desde la etiqueta class_nameTab
    2. class_objTab: prototipos (templates) y constructores para cada objeto
        2.1 Indexada por tag: en 2*tag está el protObj, en 2*tag+1 el init
    3. dispTab para cada clase
        3.1 Listado de los métodos en cada clase considerando herencia
"""

    global dispTabs

    o.p('class_nameTab')
    for className in classToID:
        o.p('.word', 'str_const' + str(classToID[className]))

    o.p('class_objTab')
    for className in classNames:
        o.p('.word', className + '_protObj')
        o.p('.word', className + '_init')

    for className in classToMethod:
        o.p(className + '_dispTab')
        methodList = []

        for methodTuple in classToMethod[className]:
            klassName = methodTuple[0]
            method = methodTuple[1]
            methodList.append(method);
            o.p('.word', klassName + '.' + method)

        dispTabs[className] = methodList


def templates(o):
    """
    El template o prototipo para cada objeto (es decir, de donde new copia al instanciar)
    1. Para cada clase generar un objeto, poner atención a:
        - nombre
        - tag
        - tamanio [tag, tamanio, dispTab, atributos ... ] = ?
            Es decir, el tamanio se calcula con base en los atributos + 3, por ejemplo
                Int tiene 1 atributo (el valor) por lo que su tamanio es 3+1
                String tiene 2 atributos (el tamanio y el valor (el 0 al final)) por lo que su tamanio es 3+2
        - dispTab
        - atributos
"""
    i = 0

    for className in classToID:
        attributes = classToAttribute[className]
        o.accum += protStr.substitute(name=className + '_protObj', disp=className + '_dispTab ', tag=i, size=len(attributes)+3)
        for classNameAttr in attributes:
            if classNameAttr == 'Int':
                o.p('.word', 'int_const0')

            elif classNameAttr == 'String':
                o.p('.word', 'str_const0')

            else:
                o.p('.word', '0')
    i += 1


def heap(o):
    o.accum += heapStr


def global_text(o):
    o.accum += textStr


def class_inits(o):
    pass


def genCode():
    o = Output()
    global_data(o)
    constants(o)
    tables(o)
    templates(o)
    heap(o)
    global_text(o)

    # Aquí enviar a un archivo, etc.
    print o.out()


def genBaseClassesAssembly():
    print("""Object_init:
	addiu	$sp $sp -12
	sw	$fp 12($sp)
	sw	$s0 8($sp)
	sw	$ra 4($sp)
	addiu	$fp $sp 4
	move	$s0 $a0
	move	$a0 $s0
	lw	$fp 12($sp)
	lw	$s0 8($sp)
	lw	$ra 4($sp)
	addiu	$sp $sp 12
	jr	$ra
IO_init:
	addiu	$sp $sp -12
	sw	$fp 12($sp)
	sw	$s0 8($sp)
	sw	$ra 4($sp)
	addiu	$fp $sp 4
	move	$s0 $a0
	jal	Object_init
	move	$a0 $s0
	lw	$fp 12($sp)
	lw	$s0 8($sp)
	lw	$ra 4($sp)
	addiu	$sp $sp 12
	jr	$ra
Int_init:
	addiu	$sp $sp -12
	sw	$fp 12($sp)
	sw	$s0 8($sp)
	sw	$ra 4($sp)
	addiu	$fp $sp 4
	move	$s0 $a0
	jal	Object_init
	move	$a0 $s0
	lw	$fp 12($sp)
	lw	$s0 8($sp)
	lw	$ra 4($sp)
	addiu	$sp $sp 12
	jr	$ra
Bool_init:
	addiu	$sp $sp -12
	sw	$fp 12($sp)
	sw	$s0 8($sp)
	sw	$ra 4($sp)
	addiu	$fp $sp 4
	move	$s0 $a0
	jal	Object_init
	move	$a0 $s0
	lw	$fp 12($sp)
	lw	$s0 8($sp)
	lw	$ra 4($sp)
	addiu	$sp $sp 12
	jr	$ra
String_init:
	addiu	$sp $sp -12
	sw	$fp 12($sp)
	sw	$s0 8($sp)
	sw	$ra 4($sp)
	addiu	$fp $sp 4
	move	$s0 $a0
	jal	Object_init
	move	$a0 $s0
	lw	$fp 12($sp)
	lw	$s0 8($sp)
	lw	$ra 4($sp)
	addiu	$sp $sp 12
	jr	$ra
""")

if __name__ == '__main__':
    # Ejecutar como: "python codegen.py <filename>" donde filename es el nombre de alguna de las pruebas
    parser = CoolParser(CommonTokenStream(CoolLexer(FileStream("input/codegen/sort_list.cool"))))
    walker = ParseTreeWalker()
    tree = parser.program()

    # Poner aquí los listeners necesarios para recorrer el árbol y obtener los datos
    # que requiere el generador de código
    walker.walk(BarridoClasesListener(), tree)
    walker.walk(DataBuilderListener(), tree)

    # Pasar parámetros al generador de código
    genCode()

    genBaseClassesAssembly()
    walker.walk(AssemblyCodePreparationListener(), tree)
    walker.walk(AssemblyCodePrintListener(), tree)

    output = ''.join(assemblyOut)
    print(output)

