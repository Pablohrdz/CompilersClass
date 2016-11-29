# coding: utf-8
from string import Template

gdStr1 = """
    .data
    .align  2
    .globl  class_nameTab
    .globl  Main_protObj
    .globl  Int_protObj
    .globl  String_protObj
    .globl  bool_const0
    .globl  bool_const1
    .globl  _int_tag
    .globl  _bool_tag
    .globl  _string_tag
"""

gdTpl1 = Template("""
_int_tag:
    .word   $intTag
_bool_tag:
    .word   $boolTag
_string_tag:
    .word   $stringTag
""")

gdStr2 = """
    .globl  _MemMgr_INITIALIZER
_MemMgr_INITIALIZER:
    .word   _NoGC_Init
    .globl  _MemMgr_COLLECTOR
_MemMgr_COLLECTOR:
    .word   _NoGC_Collect
    .globl  _MemMgr_TEST
_MemMgr_TEST:
    .word   0
"""

cTplInt = Template("""
    .word   -1
int_const$idx:
    .word   $tag
    .word   4
    .word   Int_dispTab
    .word   $value
""")

cTplStr = Template("""
    .word   -1
str_const$idx:
    .word   $tag
    .word   $size
    .word   String_dispTab
    .word   int_const$sizeIdx
    .ascii  "$value"
    .byte   0
    .align  2
""")

boolStr = """
    .word   -1
bool_const0:
    .word   3
    .word   4
    .word   Bool_dispTab
    .word   0
    .word   -1
bool_const1:
    .word   3
    .word   4
    .word   Bool_dispTab
    .word   1
"""

heapStr = """
   .globl  heap_start
heap_start:
    .word   0
"""

textStr = """
    .text
    .globl  Main_init
    .globl  Int_init
    .globl  String_init
    .globl  Bool_init
    .globl  Main.main
"""

protStr = Template("""
    .word   -1
$name
    .word $disp
    .word $tag
    .word $size
""")

############################## codegen 2
# Layout of the activation:
#
# prolog:
#
# 1. arguments in same order, on the stack
# 2. saved fp
# 3. saved s0 (self)
# 4. saved ra
# 5. locals
# 6. 4 empty bytes, new fp points here
# 7. top of the stack
#
# To address locals: n($fp) where n is an offest that lands on locals
# To address parameters: m($fp) where m is an offest that lands over the saved fp
#
# totalStack = (localsCount + 3)*4
# 3? $fp, $s0, $ra
# *4? count in words

# definir: klass, method, ts=3+locals*4, fp=ts, s0=fp-4, ra=fp-8, locals
methodTpl_in = Template("""
${klass}.${method}:
    addiu   $$sp    $$sp    -$ts        #inm: frame has $locals locals
    sw      $$fp    ${fp}($$sp)         #inm: save $$fp
    sw      $$s0    ${s0}($$sp)         #inm: save $$s0 (self)
    sw      $$ra    ${ra}($$sp)         #inm: save $$ra
    addiu   $$fp    $$sp    4           #inm: $$fp points to locals
    move    $$s0    $$a0                #inm: self to $$s0
""")

#definir klass, father
classInit = Template("""
${klass}_init
    addiu   $$sp    $$sp    -12
	sw	    $$fp    12($$sp)
	sw	    $$s0    8($$sp)
	sw	    $$ra    4($$sp)
	addiu	$$fp    $$sp 4
	move	$$s0    $$a0
	jal	    ${father}_init
	move	$$a0    $$s0
	lw	    $$fp    12($$sp)
	lw	    $$s0    8($$sp)
	lw      $$ra    4($$sp)
	addiu   $$sp    $$sp 12
	jr	    $$ra
""")

# definir: ts=3+locals*4, fp=ts, s0=fp-4, ra=fp-8, formals, locals, everything=formals+locals
methodTpl_out = Template("""
    lw      $$fp    ${ts}($$sp)         #outm: restore $fp
    lw      $$s0    ${s0}($$sp)         #outm: restore $s0 (self)
    lw      $$ra    ${ra}($$sp)         #outm: restore $ra
#outm: Clean everything! restore sp, $formals from formals, $locals from local frame
    addiu   $$sp    $$sp    $everything
    jr      $$ra                        #outm: jump and make happy the callee
""")

# definir: literal, value
litTpl = Template("""
    la      $$a0     $literal           #literal, $value
""")

selfStr = """
    move    $a0     $s0                 #self
"""

# En los letdecl, la expr es opcional...

# Si viene, simplemente emitir expr y luego poner el valor en $a0
# definir: $address, $symbol
letdeclTpl1 = Template("""
    $expr
    sw      $$a0     $address            #letdecl: initial value of $symbol
""")

# Si no viene, poner el default de cada tipo (String, Int, Bool) y en otro caso void
# definir: stringNulo, address, symbol
letdeclTpl2 = Template("""
    la      $$a0    $stringNulo         #letdecl: string nulo
    sw      $$a0    $address            #letdecl: String default value, $symbol
""")
# definir: intZero, address, symbol
letdeclTpl3 = Template("""
    la      $$a0    $intZero            #letdecl: int zero
    sw      $$a0    $address            #letdecl: Int default value, $symbol
""")
# definir: boolFalse, address, symbol
letdeclTpl2 = Template("""
    la      $$a0    $boolFalse          #letdecl: boolean false
    sw      $$a0    $address            #letdecl: Boolean default value, $symbol
""")
# definir: address, symbol
letdeclTpl2 = Template("""
    la      $$a0    $zero               #letdecl: void
    sw      $$a0    $address            #letdecl: object default value, $symbol
""")

# definir: $address, $symbol, $klass
varTpl = Template("""
    lw      $$a0     $address            #obj: load [$symbol], $klass
""")

negStr = """
    jal     Object.copy                 #neg
    lw      $t1     12($a0)             #neg
    neg     $t1     $t1                 #neg
    sw      $t1     12($a0)             #neg
"""

# definir: label
notTpl = Template("""
    lw      $$t1     12($$a0)           #not
    la      $$a0     bool_const1        #not
    beqz    $$t1     $label             #not
    la      $$a0     bool_const0        #not
$label:
""")

# definir: left_subexp, right_subexp,
arithTpl = Template("""
$left_subexp
    sw      $$a0     0($$sp)            #arith: push left subexp into the stack
    addiu   $$sp     $$sp       -4      #arith
$right_subexp
    jal     Object.copy                 #arith: get a copy to store value on
    lw      $$s1    4($$sp)             #arith: pop saved value from the stack to $$s1
    addiu   $$sp    $$sp        4       #arith
    lw      $$t2    12($$s1)            #arith: load in temp register
    lw      $$t1    12($$a0)            #arith: load in temp register
    $op     $$t1    $$t2        $$t1    #arith: operate on them
    sw      $$t1    12($$a0)            #arith: store result in copy
""")

# definir: label_false
ifTpl = Template("""
    lw      $$t1    12($$a0)            #if: get value from boolean
    beqz    $$t1    $label_false        #if: jump if false
""")

#definir:
endIfTpl = Template("""
    b       $label_exit                 #if: jump to endif
""")

# definir: label_loop, label_exit, test_subexp, loop_subexp
whileTpl = Template("""
$label_loop:
$test_subexp
    lw      $$t1    12($$a0)                #while: get value from boolean
    beq     $$t1    $$zero  $label_exit     #while: branch if false
$loop_subexp
    b       $label_loop                     #while: loop
$label_exit:
    move    $$a0    $$zero                  #while: must put void in $$a0
""")

# definir: label_exit
isVoidTpl = Template("""
$label_exit:
$subexp
    move    $$t1    $$a0                    #isvoid: load self into $$t1
    la      $$a0    bool_const1             #isvoid: load true into $$a0
    beqz    $$t1    $label_exit             #isvoid: exit if $$t1 zero (void)
    la      $$a0    bool_const0             #isvoid: otherwise, load false
$label_exit:
""")

# definir: left_subexp, right_subexp, label_exit
leTpl = Template("""
$left_subexp
    sw      $$a0    0($$sp)                 #<: push left subexp into the stack
    addiu   $$sp    $$sp    -4              #<:

$right_subexp
    lw      $$s1    4($$sp)                 #<: pop saved value from the stack into $$s1
    addiu   $$sp    $$sp     4              #<:

    lw      $$t1    12($$s1)                #<: load temp values
    lw      $$t2    12($$a0)                #<:
    la      $$a0    bool_const1             #<: load true
    ble     $$t1    $$t2                    #<: exit if less
    la      $$a0    bool_const0             #<: load false
$label_exit:
""")

# definir: left_subexp, right_subexp, label_exit
# <= El mismo que arriba pero blt en vez de ble
letTpl = Template("""
""")

# definir: left_subexp, right_subexp, label
eqTpl = Template("""
$left_subexp
    sw      $$a0    0($$sp)                 #=: push left subexp into the stack
    addiu   $$sp    $$sp    -4              #=:
$right_subexp
    lw      $$s1    4($$sp)                 #=: pop saved value from the stack into $$s1
    addiu   $$sp    $$sp     4              #=:

    move    $$t1    $$s1                    #=: load objects (addresses) to compare
    move    $$t2    $$a0                    #=:

    la      $$a0    bool_const1             #=: load true
    beq     $$t1    $$t2                    #=: if identical (same address)

    la      $$a1    bool_const0             #=: load false
    jal     equality_test                   #=: the runtime will know...
$label:
""")

# definir: exp
callParametersTpl = Template("""
$exp
    sw      $$a0    0($$sp)                 #call: push Param
    addiu   $$sp    $$sp        -4          #call:
""")

# Para el call hay 3 tipos y $$a0 cambia (instancia sobre la que se llama el método)
# 1. metodo( params ... )
callStr1 = """
    move    $$a0    $$s0                    #call: get self into $$a0
"""

# 2. (object expr).metodo( params ... )
# 3. (object expr)@Klass.metodo( params ... )
# definir: exp
callStr1 = Template("""
    $exp
""")

# definir: fileName, line, label
callTpl1 = Template("""
    bne     $$a0    $$zero      $label      #call: protect from dispatch to void
    la      $$a0    $fileName               #call: constant object with name of the file
    li      $$t1    $line                   #call: line number
    jal    _dispatch_abort                  #call: message and die
$label:
""")

# definir: off, method
callTpl_instance = Template("""
    lw      $$t1    8($$a0)                 #call: ptr to dispatch table
    lw      $$t1    $off($$t1)              #call: method $method is at offset $off
    jalr    $$t1
""")

# definir: klass, off, method
callTpl_at = Template("""
    la      $$t1    ${klass}_dispTab        #at: dispatch table for $klass
    lw      $$t1    $off($$t1)              #at: method $method is at offset $off
    jalr    $$t1
""")

# definir: address, symbol
assignTpl = Template("""
    $expr
    sw      $$a0     $address               #assignment of $symbol
""")

# definir: klass
newTpl_explicit = Template("""
    la      $$a0    ${klass}_protObj        #new: explicit name
    jal     Object.copy                     #new: call copy
    jal     ${klass}_init                   #new: call constructor
""")

newTpl_SELF_TYPE = """
    la      $$t1    class_objTab            #new: self_type, go and find class
    lw      $$t2    0($$s0)                 #new: load tag
    sll     $$t2    $$t2      3             #new: mult by 8 (4 words x 2 places (prot, init))
    addu    $$t1    $$t1      $$t2          #new: add to base to find protObj
    move    $$s1    $$t1                    #new: keep in s1 to get _init
    lw      $$a0    0($$t1)                 #new: put in $$a0 so we can
    jal     Object.copy                     #new: make a copy
    lw      $$t1    4($$s1)                 #new: add 1 word to find _init
    jalr    $$t1                            #new: call _init
"""

# definir: test_expr, fileName, line, labelNotVoid
caseTpl_begin = Template("""
    $test_expr
    bne     $$a0    $$zero  $labelVoid      #case: protect from case on void (abort)
    la      $$a0    str_const0              #case: fileName
    li      $$t1    $line                   #case: line number
    jal    _case_abort2
$labelNotVoid:
    lw      $$t1    0($$a0)                 #case: load obj tag
""")

# definir: minChild, maxChild, nLbl, address, symbol, expr, labelEnd
caseBranch = Template("""
    blt     $$t1    $minChild   $nextLbl    #case: $minChild, $name
    bgt     $$t1    $maxChild   $nextLbl    #case: $maxChild, $name
    sw      $$a0    $address                #case: $symbol
$exp
    b       $labelEnd                       #case: go to end
$nextLbl:
""")

# definir: labelEnd
caseTpl_end = Template("""
    jal     _case_abort                     #case: default
""")
