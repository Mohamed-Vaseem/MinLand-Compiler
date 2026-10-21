from flask import Flask, render_template, request
from compiler import compile_source
app=Flask(__name__)
DEFAULT="""// Edit this code and compile
let x = 10;
let y = 3;
let answer = x * 2 + y;
print(answer);
if (answer > 20) { print("greater than 20"); } else { print("20 or less"); }
"""
@app.route("/", methods=["GET","POST"])
def index():
    source=request.form.get("source",DEFAULT) if request.method=="POST" else DEFAULT
    result=compile_source(source) if request.method=="POST" else None
    return render_template("index.html",source=source,result=result)
if __name__=="__main__": app.run(debug=True)
