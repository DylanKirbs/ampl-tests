program PostOrderCalculator:
    main:
        array stack[100];
        int top = -1;

        while true:
            let inputLine = input();
            let top_type = gettop(inputLine);

            if top_type == END:
                break;
            elif top_type == SYMBOL:
                let top = top + 1;
                let stack[top] = float(inputLine);
            elif top_type == OPERATOR:
                let vals[2];

                let vals[0] = stack[top];
                let top = top - 1;
                let vals[1] = stack[top];
                let top = top - 1;

                if inputLine == "+":
                    let result = vals[1] + vals[0];
                elif inputLine == "-":
                    let result = vals[1] - vals[0];
                elif inputLine == "/":
                    let result = vals[1] / vals[0];
                elif inputLine == "*":
                    let result = vals[1] * vals[0];
                end;

                let top = top + 1;
                let stack[top] = result;
            elif top_type == NEWLINE:
                output stack[top];
                let top = top - 1;
            else:
                output "Unexpected Error";
            end;
        end;