from app import create_app

# calls the create_app function that is imported from this same directory
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)