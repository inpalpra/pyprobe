def f_lhs_rhs_sameline():
    x = 3           # L:lhs_rhs_sameline:0
    x = x + 1       # L:lhs_rhs_sameline:1
    return x

def f_augmented_assign():
    x = 10          # L:augmented_assign:0
    x += 5          # L:augmented_assign:1
    return x

def f_double_ref():
    x = 4           # L:double_ref:0
    y = x * x       # L:double_ref:1
    return y

def f_reassign_two():
    x = 3           # L:reassign_two:0
    x = x + 1       # L:reassign_two:1
    return x

def f_chain_reassign():
    x = 1           # L:chain_reassign:0
    x = 2           # L:chain_reassign:1
    x = 3           # L:chain_reassign:2
    x = 4           # L:chain_reassign:3
    return x

def f_swap():
    a = 1           # L:swap:0
    b = 2           # L:swap:1
    a, b = b, a     # L:swap:2
    return a, b

def f_loop_lhs_rhs():
    x = 100         # L:loop_lhs_rhs:0
    for i in range(5):
        x = x - 1   # L:loop_lhs_rhs:1
    return x

def f_loop_counter():
    for i in range(4):
        j = i * 2   # L:loop_counter:0
    return j

def f_accumulator():
    total = 0       # L:accumulator:0
    for i in range(1, 6):
        total = total + i # L:accumulator:1
    return total

def f_diff_funcs_foo():
    x = 10          # L:diff_funcs:0
    return x

def f_diff_funcs_bar():
    x = 20          # L:diff_funcs:1
    return x

def f_nested_shadow():
    x = 1           # L:nested_shadow:0
    def inner():
        x = 2       # L:nested_shadow:1
        return x
    inner()
    y = x           # L:nested_shadow:2
    return y

def f_recursive(n):
    x = n           # L:recursive:0
    if n > 0:
        f_recursive(n - 1)
    return

def f_conditional():
    flag = True     # L:conditional:0
    if flag:
        x = 42      # L:conditional:1
    else:
        x = 99      # L:conditional:2
    y = x           # L:conditional:3
    return y

def f_ternary():
    a = 5           # L:ternary:0
    x = a if a > 3 else 0 # L:ternary:1
    return x

def f_monotonic():
    a = 1           # L:monotonic:0
    b = a + 1       # L:monotonic:1
    c = b + 1       # L:monotonic:2
    d = c + 1       # L:monotonic:3
    return d

def f_interleaved():
    for i in range(3):
        x = i       # L:interleaved:0
        y = x + 10  # L:interleaved:1
    return

def f_multi_assign():
    a = b = c = 42  # L:multi_assign:0
    return a

def f_unpack():
    a, b, c = 1, 2, 3 # L:unpack:0
    return a

def f_exception():
    x = 1           # L:exception:0
    try:
        x = 2       # L:exception:1
        raise ValueError
        x = 999     # L:exception:2
    except:
        x = 3       # L:exception:3
    return x

x_global = 100      # L:global_local:0
def f_global_local():
    x = 1           # L:global_local:1
    return x

def f_walrus():
    data = [1, 2, 3, 4, 5]
    result = [y for x in data if (y := x * 2) > 4] # L:walrus:0
    return result

def main():
    f_lhs_rhs_sameline()
    f_augmented_assign()
    f_double_ref()
    f_reassign_two()
    f_chain_reassign()
    f_swap()
    f_loop_lhs_rhs()
    f_loop_counter()
    f_accumulator()
    f_diff_funcs_foo()
    f_diff_funcs_bar()
    f_nested_shadow()
    f_recursive(3)
    f_conditional()
    f_ternary()
    f_monotonic()
    f_interleaved()
    f_multi_assign()
    f_unpack()
    f_exception()
    f_global_local()
    f_walrus()

if __name__ == "__main__":
    main()
