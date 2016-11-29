# coding=utf-8
from parse.CoolListener import CoolListener

from structure import setBaseClasses, Klass, Method, _allClasses
from templates import *

#Estructuras de Datos Auxiliares
classNames = []
classToMethod = {}
classToAttribute = {}
classToMethodLocalsNumcalls = {}

#Para el offset
dispTabs = {}


#Constantes
constantesString = []
constantesInt = []

#Output ensamblador
assemblyOut = []


#Esta clase barre el código completo y, para cada clase, crea un objeto Klass con sus respectivos métodos y atributos.
#Dada la implementación de Klass, estas clases se guardan en el diccionario _allClasses.
class BarridoClasesListener(CoolListener):
    def __init__(self):
        setBaseClasses()

    def enterKlass(self, ctx):
        #print(ctx)

        #resetAux()
        self.currentClass = ctx.getChild(1).getText()

        if ctx.getChild(2).getText() == 'inherits':
            self.klass = Klass(ctx.getChild(1).getText(), ctx.getChild(3).getText())
        else:
            self.klass = Klass(ctx.getChild(1).getText())

    #Print params
    def enterMethod(self, ctx):
        s = len(ctx.params) + 4
        #print(ctx.params)
        #print("s -> " + str(s))
        #print(ctx.getChild(0))
        #print(ctx.getChild(s))
        self.klass.addMethod(ctx.getChild(0).getText(), Method(ctx.getChild(s)))

    def enterAttribute(self, ctx):
        #print("enterAttribute")
        #print(ctx.getChild(0))
        #print(ctx.getChild(2))
        self.klass.addAttribute(ctx.getChild(0).getText(), ctx.getChild(2).getText())

    def enterString(self, ctx):
        #print(ctx.getChild(0))
        #print(ctx.getChild(0).getText().replace('"', ''))
        #print('\n')
        constantesString.append(ctx.getChild(0).getText().replace('"', ''))

    def enterInteger(self, ctx):
        #print(ctx.getChild(0))
        #print('\n')
        constantesInt.append(ctx.getChild(0).getText())

class DataBuilderListener(CoolListener):

    def __init__(self):
        setBaseClasses()

        constantesString.append("")
        constantesInt.append('0')

        # Iterar todas las clases guardadas en _allClasses y guardar sus métodos y atributos.
        for className in _allClasses:
            classNames.append(className)
            constantesString.append(className)
            claseActual = _allClasses[className]
            flag = True

            padre = claseActual.inherits

            #Lista set de tuplas (nombre, obj método)
            methods = []

            #Lista de tipos de atributos
            attributes = []

            #Lista set de obj método
            methodSet = []

            #Repetir para los padres de las clases, hasta que se llegue a la clase 'Object'
            while True:
                #Para los métodos de la clase actual
                for method in claseActual.methods:
                    if not method in methodSet:
                        methods.append((claseActual.name, method))
                        methodSet.append(method)

                # Para los atributos de la clase actual
                for attr in claseActual.attributes:
                    attributes.append(claseActual.attributes[attr])

                if claseActual.name == 'Object':
                    break

                claseActual = _allClasses[padre]
                padre = claseActual.inherits

            classToMethod[className] = methods
            classToAttribute[className] = attributes

    def enterString(self, ctx):
        #print(ctx.getChild(0))
        #print(ctx.getChild(0).getText().replace('"', ''))
        #print('\n')
        constantesString.append(ctx.getChild(0).getText().replace('"', ''))

    def enterInteger(self, ctx):
        #print(ctx.getChild(0))
        #print('\n')
        constantesInt.append(ctx.getChild(0).getText())


    #Listener para el ensamblador

class AssemblyCodePreparationListener(CoolListener):

    def __init__(self):
        # Aux
        self.currentClass = ""
        self.currentMethod = ""
        self.currentLocals = 0
        self.numCalls = 0
        self.daddy = "Object"

    def enterKlass(self, ctx):
        global assemblyOut
        #print("enterKlass")
        #print(ctx.getChild(1))
        #print("\n")

        if ctx.getChild(2).getText() == 'inherits':
            self.daddy = ctx.getChild(3).getText()

        self.currentClass = ctx.getChild(1)

        assemblyOut.append(classInit.substitute(klass=self.currentClass, father=self.daddy))

    def enterMethod(self, ctx):
        #print("enterMethod")
        #print(ctx.getChild(0))
        #print("\n")

        self.currentMethod = ctx.getChild(0).getText()
        self.currentLocals = 0
        self.numCalls = 0


    def enterSimplecall(self, ctx):
        """print("Enter Simple Call")

        print("current_class: ")
        print(self.currentClass)
        print("\n")

        print("current_method: ")
        print(self.currentMethod)
        print("\n")

        print("call: ")
        print(ctx.getChild(0))
        print("\n")
        """
        self.numCalls += 1

    def exitMethod(self, ctx):
        global classToMethodLocalsNumcalls

        """
        print("exit_method")
        print("current_method: ")
        print(self.currentMethod)
        print("\n")

        print("current_locals: ")
        print(self.currentLocals)
        print("\n")
        """
        classToMethodLocalsNumcalls[self.currentClass] = (self.currentMethod, self.currentLocals, self.numCalls)

    def enterLet(self, ctx):
        self.currentLocals += 1

    def enterCase(self, ctx):
        self.currentLocals += 1

class AssemblyCodePrintListener(CoolListener):

    def __init__(self):
        # Aux
        self.currentClass = ""
        self.currentMethod = ""
        self.daddy = "Object"
        self.labelCount = 0

    def enterKlass(self, ctx):
        if ctx.getChild(2).getText() == 'inherits':
            self.daddy = ctx.getChild(3).getText()

        self.currentClass = ctx.getChild(1)

        # Definir el template para las nuevas clases
        #assemblyOut.append(classInit.substitute(klass=self.currentClass, father=self.daddy))

    def enterMethod(self, ctx):
        #global classToMethodLocalsNumcalls, assemblyOut

        self.currentMethod = ctx.getChild(0)
        locals = classToMethodLocalsNumcalls[self.currentClass][1]
        ts = (3 + locals) * 4
        fp = locals
        s0 = fp - 4
        ra = fp - 8
        assemblyOut.append(methodTpl_in.substitute(klass=self.currentClass, method=self.currentMethod, ts=ts, fp=fp, s0=s0, ra=ra, locals=locals))


    def enterSimplecall(self, ctx):
        global assemblyOut
        methodCalled = ctx.getChild(0)

        #TODO: Corregir este pedo
        #if methodCalled in baseClasses:
        #    assemblyOut += selfStr

        filename = "const_str0"
        line = 0
        #line = ctx.getLine()
        label = "label" + str(self.labelCount)

        assemblyOut.append(callTpl1.substitute(fileName=filename, line=line, label=label))


        method = ctx.getChild(0)
        off = 8

        #TODO: Ver qué pedo entre instance y at
        assemblyOut += callTpl_instance.substitute(method=method, off=off)

        # Desmadre de los labels
        self.labelCount += 1

    def exitMethod(self, ctx):
        global classToMethodLocalsNumcalls, assemblyOut

        #Si no hay llamadas, terminar el método con un regreso de registro
        #print("======================================================")
        #print(classToMethodLocalsNumcalls[self.currentClass][2])
        #if classToMethodLocalsNumcalls[self.currentClass][2] == 0:
        locals = classToMethodLocalsNumcalls[self.currentClass][1]
        ts = (3 + locals) * 4
        fp = ts
        s0 = fp - 4
        ra = fp - 8
        #TODO: cambiar el valor de formals acorde a lo que el prof responda
        formals = 0
        everything = formals + locals

        assemblyOut.append(methodTpl_out.substitute(ts=ts, fp=fp, s0=s0, ra=ra, formals=formals, locals=locals, everything=everything))

    def enterNew(self, ctx):
        global assemblyOut

        assemblyOut.append(newTpl_explicit.substitute(klass=self.currentClass))

    def enterLet_decl(self, ctx):
        global assemblyOut
        symbol = ctx.getChild(0)
        assemblyOut.append(letdeclTpl1.substitute(expr="", symbol=symbol, address="0($fp)"))

    def enterIf(self, ctx):
        global assemblyOut
        subexp = ctx.getChild(1).getText()

    """"
    def enterObject(self, ctx):
        global assemblyOut, dispTabs
        address = dispTabs[self.currentClass].index(self.currentMethod)
        assemblyOut.append(varTpl.substitute(address=address, symbol=ctx.getChild(0).getText(), klass=self.currentClass))
    """