import re, json
from dataclasses import dataclass, asdict
@dataclass
class Token:
    type:str
    value:str
    line:int
    column:int
class CompileError(Exception):
    def __init__(self,msg,line=None,col=None):
        self.msg,self.line,self.col=msg,line,col
    def __str__(self):
        return self.msg+(f" (line {self.line}, column {self.col})" if self.line else "")
TOKEN_RE=re.compile(r"""(?P<SPACE>[ \t\r]+)|(?P<NL>\n)|(?P<COMMENT>//[^\n]*)|(?P<NUMBER>\d+(?:\.\d+)?)|(?P<STRING>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(?P<ID>[A-Za-z_][A-Za-z0-9_]*)|(?P<OP>==|!=|<=|>=|[+\-*/%<>=!])|(?P<PUNCT>[(){},;])|(?P<BAD>.)""")
KEYWORDS={"let","print","if","else","while","true","false"}
def lex(src):
    out=[]; pos=0; line=1; col=1
    while pos<len(src):
        m=TOKEN_RE.match(src,pos); k,v=m.lastgroup,m.group(); pos=m.end()
        if k=="NL": line+=1; col=1; continue
        if k in ("SPACE","COMMENT"): col+=len(v); continue
        if k=="BAD": raise CompileError(f"Unexpected character {v!r}",line,col)
        if k=="ID" and v in KEYWORDS: k="KEYWORD"
        out.append(Token(k,v,line,col)); col+=len(v)
    out.append(Token("EOF","",line,col)); return out
class Parser:
    def __init__(self,t): self.t=t; self.i=0
    @property
    def c(self): return self.t[self.i]
    def eat(self,v=None,k=None):
        x=self.c
        if v is not None and x.value!=v: raise CompileError(f"Expected {v!r}, found {x.value!r}",x.line,x.column)
        if k is not None and x.type!=k: raise CompileError(f"Expected {k}, found {x.type} ({x.value!r})",x.line,x.column)
        self.i+=1; return x
    def parse(self):
        b=[]
        while self.c.type!="EOF": b.append(self.stmt())
        return {"type":"Program","body":b}
    def stmt(self):
        if self.c.value=="let":
            self.eat("let"); n=self.eat(k="ID"); self.eat("="); e=self.expr(); self.eat(";")
            return {"type":"Let","name":n.value,"value":e,"line":n.line}
        if self.c.value=="print":
            self.eat("print"); self.eat("("); e=self.expr(); self.eat(")"); self.eat(";"); return {"type":"Print","value":e}
        if self.c.value=="if":
            self.eat("if"); self.eat("("); test=self.expr(); self.eat(")"); yes=self.block(); no=[]
            if self.c.value=="else": self.eat("else"); no=self.block()
            return {"type":"If","test":test,"yes":yes,"no":no}
        if self.c.value=="while":
            self.eat("while"); self.eat("("); test=self.expr(); self.eat(")"); return {"type":"While","test":test,"body":self.block()}
        if self.c.type=="ID":
            n=self.eat(k="ID"); self.eat("="); e=self.expr(); self.eat(";")
            return {"type":"Assign","name":n.value,"value":e,"line":n.line}
        raise CompileError(f"Unexpected token {self.c.value!r}; expected statement",self.c.line,self.c.column)
    def block(self):
        self.eat("{"); b=[]
        while self.c.value!="}":
            if self.c.type=="EOF": raise CompileError("Unterminated block",self.c.line,self.c.column)
            b.append(self.stmt())
        self.eat("}"); return b
    def expr(self): return self.eq()
    def chain(self,lower,ops):
        n=lower()
        while self.c.value in ops:
            op=self.eat().value; n={"type":"Binary","op":op,"left":n,"right":lower()}
        return n
    def eq(self): return self.chain(self.cmp,("==","!="))
    def cmp(self): return self.chain(self.term,("<",">","<=",">="))
    def term(self): return self.chain(self.factor,("+","-"))
    def factor(self): return self.chain(self.unary,("*","/","%"))
    def unary(self):
        if self.c.value in ("!","-"):
            op=self.eat().value; return {"type":"Unary","op":op,"value":self.unary()}
        return self.primary()
    def primary(self):
        x=self.c
        if x.type=="NUMBER":
            self.eat(); return {"type":"Literal","value":float(x.value) if "." in x.value else int(x.value)}
        if x.type=="STRING":
            self.eat()
            try: val=json.loads(x.value) if x.value.startswith('"') else x.value[1:-1]
            except Exception: val=x.value[1:-1]
            return {"type":"Literal","value":val}
        if x.value in ("true","false"): self.eat(); return {"type":"Literal","value":x.value=="true"}
        if x.type=="ID": self.eat(); return {"type":"Variable","name":x.value,"line":x.line}
        if x.value=="(": self.eat("("); n=self.expr(); self.eat(")"); return n
        raise CompileError(f"Expected expression, found {x.value!r}",x.line,x.column)
def semantic(ast):
    declared=set()
    def ev(n):
        if n["type"]=="Variable" and n["name"] not in declared: raise CompileError(f"Variable {n['name']!r} used before declaration",n.get("line"))
        if n["type"]=="Binary": ev(n["left"]); ev(n["right"])
        if n["type"]=="Unary": ev(n["value"])
    def walk(ss):
        for s in ss:
            t=s["type"]
            if t=="Let":
                if s["name"] in declared: raise CompileError(f"Variable {s['name']!r} already declared",s.get("line"))
                ev(s["value"]); declared.add(s["name"])
            elif t=="Assign":
                if s["name"] not in declared: raise CompileError(f"Assignment to undeclared variable {s['name']!r}",s.get("line"))
                ev(s["value"])
            elif t=="Print": ev(s["value"])
            elif t=="If": ev(s["test"]); walk(s["yes"]); walk(s["no"])
            elif t=="While": ev(s["test"]); walk(s["body"])
    walk(ast["body"])
class IR:
    def __init__(self): self.lines=[]; self.nt=0; self.nl=0
    def temp(self): self.nt+=1; return "t"+str(self.nt)
    def label(self,p): self.nl+=1; return p+str(self.nl)
    def expr(self,n):
        if n["type"]=="Literal": return repr(n["value"])
        if n["type"]=="Variable": return n["name"]
        if n["type"]=="Unary":
            v=self.expr(n["value"]); t=self.temp(); self.lines.append(f"{t} = {n['op']}{v}"); return t
        a=self.expr(n["left"]); b=self.expr(n["right"]); t=self.temp()
        self.lines.append(f"{t} = {a} {n['op']} {b}"); return t
    def walk(self,ss):
        for s in ss:
            t=s["type"]
            if t in ("Let","Assign"): self.lines.append(f"{s['name']} = {self.expr(s['value'])}")
            elif t=="Print": self.lines.append("PRINT "+self.expr(s["value"]))
            elif t=="If":
                c=self.expr(s["test"]); other=self.label("ELSE"); end=self.label("END")
                self.lines += [f"IF_FALSE {c} GOTO {other}"]; self.walk(s["yes"]); self.lines.append(f"GOTO {end}")
                self.lines.append("LABEL "+other); self.walk(s["no"]); self.lines.append("LABEL "+end)
            elif t=="While":
                start=self.label("WHILE"); end=self.label("END"); self.lines.append("LABEL "+start)
                c=self.expr(s["test"]); self.lines.append(f"IF_FALSE {c} GOTO {end}"); self.walk(s["body"])
                self.lines += [f"GOTO {start}","LABEL "+end]
def execute(ast):
    env={}; out=[]
    def ev(n):
        t=n["type"]
        if t=="Literal": return n["value"]
        if t=="Variable": return env[n["name"]]
        if t=="Unary":
            v=ev(n["value"]); return not v if n["op"]=="!" else -v
        a,b=ev(n["left"]),ev(n["right"])
        return {"+":lambda:a+b,"-":lambda:a-b,"*":lambda:a*b,"/":lambda:a/b,"%":lambda:a%b,
        "==":lambda:a==b,"!=":lambda:a!=b,"<":lambda:a<b,">":lambda:a>b,"<=":lambda:a<=b,">=":lambda:a>=b}[n["op"]]()
    def run(ss):
        for s in ss:
            t=s["type"]
            if t=="Let": env[s["name"]]=ev(s["value"])
            elif t=="Assign": env[s["name"]]=ev(s["value"])
            elif t=="Print": out.append(str(ev(s["value"])))
            elif t=="If": run(s["yes"] if ev(s["test"]) else s["no"])
            elif t=="While":
                count=0
                while ev(s["test"]):
                    count+=1
                    if count>10000: raise CompileError("Loop iteration limit exceeded")
                    run(s["body"])
    run(ast["body"]); return out,env
def compile_source(source):
    try:
        ts=lex(source); ast=Parser(ts).parse(); semantic(ast); ir=IR(); ir.walk(ast["body"]); out,env=execute(ast)
        return {"ok":True,"tokens":[asdict(t) for t in ts if t.type!="EOF"],"ast":json.dumps(ast,indent=2),
        "ir":"\n".join(ir.lines),"output":"\n".join(out) if out else "(no output)","symbols":json.dumps(env,indent=2),"error":None}
    except (CompileError,ZeroDivisionError,TypeError,KeyError) as e:
        return {"ok":False,"tokens":[],"ast":"","ir":"","output":"","symbols":"","error":str(e) if isinstance(e,CompileError) else f"Runtime error: {e}"}
