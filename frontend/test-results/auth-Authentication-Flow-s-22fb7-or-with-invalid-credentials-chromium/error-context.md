# Page snapshot

```yaml
- generic [ref=e4]:
  - generic [ref=e5]:
    - img [ref=e7]
    - heading "Welcome Back" [level=2] [ref=e10]
    - paragraph [ref=e11]: Sign in to your AP2 Expense account
  - generic [ref=e12]:
    - img [ref=e13]
    - paragraph [ref=e15]: Incorrect username or password
  - generic [ref=e16]:
    - generic [ref=e17]:
      - generic [ref=e18]: Username
      - generic [ref=e19]:
        - img [ref=e20]
        - textbox "Enter your username" [ref=e23]: invaliduser
    - generic [ref=e24]:
      - generic [ref=e25]: Password
      - generic [ref=e26]:
        - img [ref=e27]
        - textbox "Enter your password" [ref=e30]: wrongpassword
        - button [ref=e31] [cursor=pointer]:
          - img [ref=e32]
    - button "Sign In" [ref=e35] [cursor=pointer]
  - generic [ref=e36]:
    - generic [ref=e41]: Or continue with
    - button "Continue with Google" [ref=e42] [cursor=pointer]:
      - img [ref=e43]
      - text: Continue with Google
  - paragraph [ref=e49]:
    - text: Don't have an account?
    - button "Sign up" [ref=e50] [cursor=pointer]
```