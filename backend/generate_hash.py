import sys
import bcrypt

def main():
    print("="*50)
    print("🔒 Affiliate Video Maker - Password Hash Generator")
    print("="*50)
    password = input("Masukkan password yang ingin digunakan untuk login: ").strip()
    
    if not password:
        print("Password tidak boleh kosong!")
        sys.exit(1)
        
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    print("\n✅ Berhasil! Salin teks di bawah ini dan paste ke dalam file backend/.env:\n")
    print(f"ADMIN_PASSWORD_HASH={hashed}")
    print("\nCatatan: Jangan lupa membuat JWT_SECRET juga di .env, misalnya:")
    print("JWT_SECRET=rahasia123456789")

if __name__ == "__main__":
    main()
