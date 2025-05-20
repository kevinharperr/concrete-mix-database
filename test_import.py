from sequential_import import import_reference_data, import_materials, import_ds1, import_ds2

# Run the functions sequentially with proper error handling
print("\n*** STARTING TEST IMPORT ***\n")

print("\n=== IMPORTING REFERENCE DATA ===\n")
success = import_reference_data()
print(f"Reference data import {'succeeded' if success else 'failed'}")

if success:
    print("\n=== IMPORTING MATERIALS ===\n")
    success = import_materials()
    print(f"Materials import {'succeeded' if success else 'failed'}")

if success:
    print("\n=== IMPORTING DATASET 1 ===\n")
    success = import_ds1()
    print(f"Dataset 1 import {'succeeded' if success else 'failed'}")

if success:
    print("\n=== IMPORTING DATASET 2 ===\n")
    success = import_ds2()
    print(f"Dataset 2 import {'succeeded' if success else 'failed'}")

# DS3 import not yet implemented
# if success:
#     print("\n=== IMPORTING DATASET 3 ===\n")
#     success = import_ds3()
#     print(f"Dataset 3 import {'succeeded' if success else 'failed'}")

print("\n*** TEST IMPORT COMPLETE ***\n")
